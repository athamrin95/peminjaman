import sqlite3
import threading
import pytest
import aturan
from aturan import confirmation, pinjam, cari_perangkat
from penyimpanan import get_records, setup_table


def test_cari_perangkat_empty_string():
    """Test that passing an empty string returns the appropriate error dictionary."""
    result = cari_perangkat("")
    assert result == {"error": "Passed an empty string as the argument!"}


def test_cari_perangkat_by_code_exact():
    """Test matching an exact item code (case-sensitive)."""
    result = cari_perangkat("LP-01")
    assert "success" in result
    assert "LP-01" in result["success"]


def test_cari_perangkat_by_code_case_insensitive():
    """Test matching a code using different casing."""
    result = cari_perangkat("lp-02")
    assert "success" in result
    assert "LP-02" in result["success"]


def test_cari_perangkat_by_name_multiple():
    """Test matching a name that returns multiple items from PSEUDO_DB."""
    result = cari_perangkat("Laptop 14 inch")
    assert "success" in result
    assert "LP-01" in result["success"]
    assert "LP-02" in result["success"]


def test_cari_perangkat_by_type():
    """Test matching an item type."""
    result = cari_perangkat("projector")
    assert "success" in result
    assert "PR-01" in result["success"]


def test_cari_perangkat_no_match():
    """Test that a non-existent query returns a no match error dictionary."""
    result = cari_perangkat("NonExistentItem")
    assert result == {"error": "No match found in the database!"}


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Create a temporary SQLite DB via setup_table, point DB_PATH to it, and seed rows."""
    db_file = tmp_path / "test_peminjaman.db"
    monkeypatch.setattr(aturan, "DB_PATH", str(db_file))

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


def test_pinjam_conflicting_schedule(temp_db, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")

    result = pinjam("LP-01", "Dodi", "2026-11-23", 2, confirmation)

    assert "error" in result
    assert len(get_records(temp_db)) == 2


def test_pinjam_confirmed(temp_db, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")

    result = pinjam("LP-01", "Andi", "2026-11-25", 2, confirmation)

    assert "error" not in result
    rows = get_records(temp_db)
    assert len(rows) == 3
    assert rows[-1][1:] == ("LP-01", "Andi", "2026-11-25", "2026-11-27")


def test_pinjam_declined(temp_db, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "n")

    result = pinjam("CM-01", "Rina", "2026-11-21", 3, confirmation)

    assert "error" in result
    rows = get_records(temp_db)
    # Still only the 2 seeded rows
    assert len(rows) == 2
    assert all(row[2] != "Rina" for row in rows)


def test_pinjam_validation_error_name_empty(temp_db, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")

    result = pinjam("LP-01", "   ", "2026-11-26", 2, confirmation)

    assert result == {"error": "The borrower's name cannot be empty!"}
    assert len(get_records(temp_db)) == 2


def test_pinjam_validation_error_code_not_in_pseudo_db(temp_db, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "y")

    result = pinjam("LP-99", "Budi", "2026-11-21", 2, confirmation)

    assert result == {"error": "Device LP-99 not found in database!"}
    assert len(get_records(temp_db)) == 2


@pytest.mark.parametrize("bad_date", ["21-11-2026", "2026/11/21", "2026-13-01", "not-a-date"])
def test_pinjam_validation_error_date_must_follow_yyyy_mm_dd(temp_db, monkeypatch, bad_date):
    monkeypatch.setattr("builtins.input", lambda _: "y")

    result = pinjam("LP-01", "Budi", bad_date, 2, confirmation)

    assert result == {
        "error": f"The given date {bad_date} must follow the format YYYY-MM-DD!"
    }
    assert len(get_records(temp_db)) == 2


@pytest.mark.parametrize("bad_duration", [0, -3, 8, 14])
def test_pinjam_validation_error_duration_must_be_between_1_and_7(temp_db, monkeypatch, bad_duration):
    monkeypatch.setattr("builtins.input", lambda _: "y")

    result = pinjam("LP-01", "Budi", "2026-11-21", bad_duration, confirmation)

    assert result == {
        "error": "The borrowing duration must be between 1 - 7 days!"
    }
    assert len(get_records(temp_db)) == 2


def test_pinjam_two_threads_same_time_slot(temp_db):
    barrier = threading.Barrier(2)

    def barrier_confirmation(message:str) -> bool:
        message = "y"
        barrier.wait(timeout=5.0)
        return message == "y"

    results: list[dict] = []
    lock = threading.Lock()

    def worker(borrower: str) -> None:
        res = pinjam("LP-01", borrower, "2026-11-26", 2, barrier_confirmation)
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

    # Only 1 new row should be added on top of the 2 seeded rows in temp_db
    rows = get_records(temp_db)
    assert len(rows) == 3
    assert rows[-1][1] == "LP-01"
    assert rows[-1][3:] == ("2026-11-26", "2026-11-28")