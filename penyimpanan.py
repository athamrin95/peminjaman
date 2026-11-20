import sqlite3


def setup_table(db_path:str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE IF NOT EXISTS peminjaman (id INTEGER PRIMARY KEY, code TEXT NOT NULL, borrower TEXT NOT NULL, start TEXT NOT NULL, end TEXT NOT NULL)")
    conn.commit()
    conn.close()

def get_records(db_path: str, date: str | None = None) -> list:
    """Returns all records from the database, or if a date is given, records of device(s) that are being borrowed at the given date"""
    conn = sqlite3.connect(db_path)
    records_found = []
    if date is None:
        records_found = conn.execute("SELECT id, code, borrower, start, end FROM peminjaman").fetchall()
    else:
        records_found = conn.execute("SELECT id, code, borrower, start, end FROM peminjaman WHERE start <= ? AND ? < end", (date,date,)).fetchall()
    conn.close()
    return records_found

def get_devices(db_path:str, start_date:str, end_date:str) -> list:
    """Returns all device(s) that have a conflicting schedule with the given start and end date"""
    conn = sqlite3.connect(db_path)
    devices_found = []
    devices_found = conn.execute("SELECT id, code, borrower, start, end FROM peminjaman WHERE start < ? AND ? < end", (end_date, start_date,)).fetchall()
    conn.close()
    return devices_found

def check_conflict(db_path:str, code:str, start_date:str, end_date:str) -> tuple | None:
    conn = sqlite3.connect(db_path)
    found = conn.execute("SELECT id, code, borrower, start, end FROM peminjaman WHERE start < ? AND ? < end AND code = ?", (end_date, start_date, code,)).fetchone()
    conn.close()
    return found

def insert_record(db_path:str, code:str, name:str, start_date:str, end_date:str) -> dict | None:
    conn = sqlite3.connect(db_path)
    conn.execute("BEGIN IMMEDIATE")
    # Check conflict again
    found = conn.execute("SELECT id, code, borrower, start, end FROM peminjaman WHERE start < ? AND ? < end AND code = ?", (end_date, start_date, code,)).fetchone()
    if found is not None:
        conn.rollback()
        conn.close()
        return None

    conn.execute("INSERT INTO peminjaman (code, borrower, start, end) VALUES (?, ?, ?, ?)", (code, name, start_date, end_date,))
    conn.commit()
    conn.close()
    return {"success": f"The item {code} has been successfully borrowed under the name of {name} from {start_date} to {end_date}!"}
