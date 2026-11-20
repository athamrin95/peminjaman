import sqlite3


def main() -> None:
    conn = sqlite3.connect("coba.db")
    conn.execute("CREATE TABLE IF NOT EXISTS catatan (id INTEGER PRIMARY KEY, isi TEXT NOT NULL)")
    conn.execute("INSERT INTO catatan (isi) VALUES (?)", ("cek laptop",))
    conn.execute("INSERT INTO catatan (isi) VALUES (?)", ("cek kamera",))
    conn.commit()
    rows = conn.execute("SELECT id, isi FROM catatan").fetchall()
    for row in rows:
        print(row)
    print(f"Where id is 1: {conn.execute("SELECT id, isi FROM catatan WHERE id = 1").fetchall()}")
    conn.close()

if __name__ == "__main__":
    main()