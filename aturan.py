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