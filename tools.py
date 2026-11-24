from datetime import datetime, timedelta
from langchain.tools import tool
from aturan import DB_PATH, cari_perangkat, periksa_argumen_pinjam
from penyimpanan import get_records, insert_record
from langchain.agents.middleware import ToolCallRequest


@tool
def find_existing_devices(text:str) -> dict:
    """Find existing device(s) from the database given the word/text argument that is used to find and match said device(s)"""
    return cari_perangkat(text)

@tool
def find_borrowed_devices(date_string:str) -> dict:
    """Find all the devices that are being borrowed from the database given the date. The date_string argument must be in YYYY-MM-DD format"""
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
    except ValueError:
        return {"error": f"The given date {date_string} must follow the format YYYY-MM-DD!"}

    found = get_records(DB_PATH, date_string)
    return {"success": f"Found the following {found}. Note that each element within the list (if not empty) is a tuple with the following format: id, device codename, borrower name, start_date, and end_date."}

@tool
def borrow_a_device(device_code_name:str, borrower_name:str, start_date:str, borrow_duration_in_days:int) -> dict:
    """Begin the process of borrowing a device when user wishes to do so. The start_date argument must be given in YYYY-MM-DD format"""
    return pinjam(device_code_name, borrower_name, start_date, borrow_duration_in_days)

def pinjam(code:str, name:str, date:str, duration:int) -> dict:
    result = periksa_argumen_pinjam(code, name, date, duration)
    if result is not None:
        return result

    start_date = datetime.strptime(date, "%Y-%m-%d").date()
    end_date = start_date + timedelta(days=duration)
    start_date_str = str(start_date)
    end_date_str = str(end_date)

    result = insert_record(DB_PATH, code, name, start_date_str, end_date_str)
    if result is None:
        return{"error": f"There is a conflicting schedule for {code} for the selected date {start_date_str} to {end_date_str}."}

    return result

def check_borrow_conditions(request: ToolCallRequest) -> bool:
    """Return True to pause for human approval only when everything meets the requirement, else return False to let the tool run without interrupting to return an error statement"""
    code = request.tool_call["args"].get("device_code_name", "")
    name = request.tool_call["args"].get("borrower_name", "")
    date = request.tool_call["args"].get("start_date", "")
    duration = request.tool_call["args"].get("borrow_duration_in_days", 0)
    return periksa_argumen_pinjam(code, name, date, duration) is None


ALL_TOOLS = [find_existing_devices, find_borrowed_devices, borrow_a_device]