from datetime import datetime, timedelta
from penyimpanan import check_conflict


DB_PATH = "peminjaman.db"

DEVICES = [
    {"code":"LP-01", "name":"Laptop 14 inch", "type":"laptop"},
    {"code":"LP-02", "name":"Laptop 14 inch", "type":"laptop"},
    {"code":"PR-01", "name":"Projector", "type":"projector"},
    {"code":"CM-01", "name":"Camera", "type":"camera"},
]

def cari_perangkat(text:str) -> dict:
    if text == "":
        return {"error":"Passed an empty string as the argument!"}

    found_list = []
    for entry in DEVICES:
        if entry["code"].casefold() == text.casefold() or entry["name"].casefold() == text.casefold() or entry["type"].casefold() == text.casefold():
            found_list.append(entry)

    if len(found_list) == 0:
        return {"error":"No match found in the database!"}
    
    return {"success":f"Found the following: {found_list}."}

def periksa_argumen_pinjam(code:str, name:str, date:str, duration:int) -> dict | None:
    # code must be found in PSEUDO_DB
    code_found = False
    for entry in DEVICES:
        if entry["code"].casefold() == code.casefold():
            code_found = True
            break
    if not code_found:
        return {"error": f"Device {code} not found in database!"}

    # name must not be empty
    if name.strip() == "":
        return {"error": "The borrower's name cannot be empty!"}

    # date must follow the format YYYY-MM-DD
    try:
        start_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return {"error": f"The given date {date} must follow the format YYYY-MM-DD!"}

    # duration must be between 1 - 7 (days)
    if duration < 1 or duration > 7:
        return {"error": "The borrowing duration must be between 1 - 7 days!"}

    # Check if there is a conflicting schedule in the database
    end_date = start_date + timedelta(days=duration)
    start_date_str = str(start_date)
    end_date_str = str(end_date)
    if check_conflict(DB_PATH, code, start_date_str, end_date_str) is not None:
        return{"error": f"There is a conflicting schedule for {code} for the selected date {start_date_str} to {end_date_str}."}

    # Success! No error is found
    return None