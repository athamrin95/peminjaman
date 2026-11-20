from datetime import datetime
from langchain.tools import tool
from aturan import DB_PATH, cari_perangkat
from penyimpanan import get_records


@tool
def find_existing_devices(text:str):
    """Find existing device(s) from the database given the word/text argument that is used to find and match said device(s)"""
    return cari_perangkat(text)

@tool
def find_borrowed_devices(date_string:str):
    """Find all the devices that are being borrowed from the database given the date. The date_string argument must be in YYYY-MM-DD format"""
    try:
        date = datetime.strptime(date_string, "%Y-%m-%d")
    except ValueError:
        return {"error": f"The given date {date_string} must follow the format YYYY-MM-DD!"}

    found = get_records(DB_PATH, date)
    return {"success": f"Found the following {found}. Note that each element within the list (if not empty) is a tuple with the following format: id, device codename, borrower name, start_date, and end_date."}

ALL_TOOLS = [find_existing_devices, find_borrowed_devices]