import sqlite3

import pytest

from aturan import cari_perangkat, periksa_argumen_pinjam
import aturan
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
    """Create a temporary SQLite DB via setup_table, point aturan.DB_PATH to it, and seed rows."""
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

def test_periksa_argumen_pinjam_valid(temp_db):
    """Valid device, borrower, date, duration, and non-conflicting schedule return None."""
    result = periksa_argumen_pinjam("LP-01", "Andi", "2026-11-25", 2)
    assert result is None
    assert len(get_records(temp_db)) == 2


def test_periksa_argumen_pinjam_case_insensitive_code(temp_db):
    """Device code lookup should be case-insensitive."""
    result = periksa_argumen_pinjam("lp-02", "Andi", "2026-11-25", 2)
    assert result is None


def test_periksa_argumen_pinjam_unknown_device(temp_db):
    """Unknown device code returns an error dictionary."""
    result = periksa_argumen_pinjam("LP-99", "Andi", "2026-11-25", 2)
    assert result == {"error": "Device LP-99 not found in database!"}


@pytest.mark.parametrize("bad_name", ["", "   ", "\t\n"])
def test_periksa_argumen_pinjam_empty_name(temp_db, bad_name):
    """Blank or whitespace-only borrower name returns an error dictionary."""
    result = periksa_argumen_pinjam("LP-01", bad_name, "2026-11-25", 2)
    assert result == {"error": "The borrower's name cannot be empty!"}


@pytest.mark.parametrize("bad_date", ["25-11-2026", "2026/11/25", "2026-13-01", "not-a-date"])
def test_periksa_argumen_pinjam_invalid_date(temp_db, bad_date):
    """Dates not matching YYYY-MM-DD return an error dictionary."""
    result = periksa_argumen_pinjam("LP-01", "Andi", bad_date, 2)
    assert result == {
        "error": f"The given date {bad_date} must follow the format YYYY-MM-DD!"
    }


@pytest.mark.parametrize("bad_duration", [0, -1, 8, 14])
def test_periksa_argumen_pinjam_invalid_duration(temp_db, bad_duration):
    """Duration outside 1..7 days returns an error dictionary."""
    result = periksa_argumen_pinjam("LP-01", "Andi", "2026-11-25", bad_duration)
    assert result == {
        "error": "The borrowing duration must be between 1 - 7 days!"
    }


def test_periksa_argumen_pinjam_conflicting_schedule(temp_db):
    """Overlapping booking window for the same device returns a conflict error."""
    # Seeded LP-01 is 2026-11-22 to 2026-11-25; 2026-11-23 for 2 days -> 2026-11-23 to 2026-11-25 overlaps
    result = periksa_argumen_pinjam("LP-01", "Dodi", "2026-11-23", 2)
    assert result == {
        "error": "There is a conflicting schedule for LP-01 for the selected date 2026-11-23 to 2026-11-25."
    }