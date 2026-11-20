from datetime import datetime, timedelta
from penyimpanan import check_conflict, insert_record


DB_PATH = "peminjaman.db"

PSEUDO_DB = [
    {"code":"LP-01", "name":"Laptop 14 inch", "type":"laptop"},
    {"code":"LP-02", "name":"Laptop 14 inch", "type":"laptop"},
    {"code":"PR-01", "name":"Projector", "type":"projector"},
    {"code":"CM-01", "name":"Camera", "type":"camera"},
]

def cari_perangkat(text:str) -> dict:
    if text == "":
        return {"error":"Passed an empty string as the argument!"}

    found_list = []
    for entry in PSEUDO_DB:
        if entry["code"].casefold() == text.casefold() or entry["name"].casefold() == text.casefold() or entry["type"].casefold() == text.casefold():
            found_list.append(entry)

    if len(found_list) == 0:
        return {"error":"No match found in the database!"}
    
    return {"success":f"Found the following: {found_list}."}

def confirmation(message:str) -> bool:
    user_input = input(f"{message}. (y/n)? ")
    if user_input.strip().casefold() == "y":
        return True
    else:
        return False

def pinjam(code:str, name:str, date:str, duration:int, confirmation) -> dict:
    # code must be found in PSEUDO_DB
    code_found = False
    for entry in PSEUDO_DB:
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
    
    end_date = start_date + timedelta(days=duration)
    start_date = str(start_date)
    end_date = str(end_date)
    # The same device (denoted by their code) cannot be borrowed by multiple person at any given time
    if check_conflict(DB_PATH, code, start_date, end_date) is not None:
        return{"error": f"There is a conflicting schedule for {code} for the selected date {start_date} to {end_date}."}

    message = f"Confirm the borrowing of {code} under the name of {name} from {start_date} to {end_date}."
    if not confirmation(message):
        return {"error": f"User has selected to not confirm the borrowing of {code} under the name of {name} from {start_date} to {end_date}."}

    result = insert_record(DB_PATH, code, name, start_date, end_date)
    if result is None:
        return{"error": f"There is a conflicting schedule for {code} for the selected date {start_date} to {end_date}."}

    return result