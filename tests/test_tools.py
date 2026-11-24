import sqlite3
import threading
import pytest
import aturan
from penyimpanan import get_records, setup_table
from tools import find_borrowed_devices, pinjam
import tools


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Create a temporary SQLite DB via setup_table, point DB_PATH to it, and seed rows."""
    db_file = tmp_path / "test_peminjaman.db"
    monkeypatch.setattr(aturan, "DB_PATH", str(db_file))
    monkeypatch.setattr(tools, "DB_PATH", str(db_file))

    setup_table(str(db_file))

    conn = sqlite3.connect(db_file)
    conn.executemany(
        "INSERT INTO peminjaman (code, borrower, start, end) VALUES (?, ?, ?, ?)",
        [
            ("LP-01", "Budi", "2026-11-22", "2026-11-25"),
            ("PR-01", "Sari", "2026-11-21", "2026-11-23"),
        ],
    )
    conn.commit()
    conn.close()
    return str(db_file)


def test_pinjam_conflicting_schedule(temp_db):
    result = pinjam("LP-01", "Dodi", "2026-11-23", 2)

    assert "error" in result
    assert len(get_records(temp_db)) == 2


def test_pinjam_success(temp_db):
    result = pinjam("LP-01", "Andi", "2026-11-25", 2)

    assert "error" not in result
    rows = get_records(temp_db)
    assert len(rows) == 3
    assert rows[-1][1:] == ("LP-01", "Andi", "2026-11-25", "2026-11-27")


def test_pinjam_validation_error_name_empty(temp_db):
    result = pinjam("LP-01", "   ", "2026-11-26", 2)

    assert result == {"error": "The borrower's name cannot be empty!"}
    assert len(get_records(temp_db)) == 2


def test_pinjam_validation_error_code_not_in_devices(temp_db):
    result = pinjam("LP-99", "Budi", "2026-11-21", 2)

    assert result == {"error": "Device LP-99 not found in database!"}
    assert len(get_records(temp_db)) == 2


@pytest.mark.parametrize("bad_date", ["21-11-2026", "2026/11/21", "2026-13-01", "not-a-date"])
def test_pinjam_validation_error_date_must_follow_yyyy_mm_dd(temp_db, bad_date):
    result = pinjam("LP-01", "Budi", bad_date, 2)

    assert result == {
        "error": f"The given date {bad_date} must follow the format YYYY-MM-DD!"
    }
    assert len(get_records(temp_db)) == 2


@pytest.mark.parametrize("bad_duration", [0, -3, 8, 14])
def test_pinjam_validation_error_duration_must_be_between_1_and_7(temp_db, bad_duration):
    result = pinjam("LP-01", "Budi", "2026-11-21", bad_duration)

    assert result == {
        "error": "The borrowing duration must be between 1 - 7 days!"
    }
    assert len(get_records(temp_db)) == 2


def test_pinjam_two_threads_same_time_slot(temp_db, monkeypatch):
    barrier = threading.Barrier(2)
    original_insert_record = tools.insert_record

    def barrier_insert_record(db_path: str, code: str, name: str, start_date: str, end_date: str) -> dict | None:
        barrier.wait(timeout=5.0)
        return original_insert_record(db_path, code, name, start_date, end_date)

    monkeypatch.setattr(tools, "insert_record", barrier_insert_record)

    results: list[dict] = []
    lock = threading.Lock()

    def worker(borrower: str) -> None:
        res = pinjam("LP-01", borrower, "2026-11-26", 2)
        with lock:
            results.append(res)

    t1 = threading.Thread(target=worker, args=("Andi",))
    t2 = threading.Thread(target=worker, args=("Budi",))
    t1.start()
    t2.start()
    t1.join(timeout=5.0)
    t2.join(timeout=5.0)

    successes = [r for r in results if "error" not in r]
    failures = [r for r in results if "error" in r]

    assert len(results) == 2
    assert len(successes) == 1
    assert len(failures) == 1
    assert "conflicting schedule" in failures[0]["error"]

    rows = get_records(temp_db)
    assert len(rows) == 3
    assert rows[-1][1] == "LP-01"
    assert rows[-1][3:] == ("2026-11-26", "2026-11-28")

def test_find_borrowed_devices_active_on_date(temp_db):
    result = find_borrowed_devices.invoke({"date_string": "2026-11-22"})

    assert "success" in result
    assert "LP-01" in result["success"]
    assert "Budi" in result["success"]
    assert "PR-01" in result["success"]
    assert "Sari" in result["success"]


def test_find_borrowed_devices_none_on_date(temp_db):
    result = find_borrowed_devices.invoke({"date_string": "2026-11-25"})

    assert "success" in result
    assert "[]" in result["success"]


@pytest.mark.parametrize("bad_date", ["22-11-2026", "2026/11/22", "2026-13-01", "invalid"])
def test_find_borrowed_devices_invalid_date_format(temp_db, bad_date):
    result = find_borrowed_devices.invoke({"date_string": bad_date})

    assert result == {
        "error": f"The given date {bad_date} must follow the format YYYY-MM-DD!"
    }