This project showcases the ChatOpenAI class (LangChain integration wrapper for OpenAI's chat models).<br>

`cek_model.py`:<br>
This script simply checks if the code is working properly by sending/invoking a question to the AI and receiving a proper response from it.<br>

`asistent.py`:<br>
This script uses the LangChain agent framework to give the AI the necessary tool to execute user's query to find the requested item information from the
"database" (`DEVICES`). Information regarding the lending/borrowing record of devices is stored in a SQLite database (`peminjaman.db`, which will be created if none exist).<br>
Currently one can ask the agent to check if a given device can be found in the "database" and to check if said device is currently being borrowed at a given date. Next version will include adding the ability to ask the agent to borrow a device.<br>
Available local command:<br>
- `/keluar`: Exits the script.<br>
- `/perangkat`: Prints all the item information stored in `DEVICES` variable in `aturan.py`.<br>

`coba_sqlite.py`:<br>
This script creates an empty database file called `coba.db`, adds 2 entries to it (table `catatan`) and prints them out to the terminal.<br>

`coba_api.py`:<br>
This script is a simple localhost webserver (for API testing) that uses FastAPI (run this with uvicorn).<br>

`asisten_app.py`:<br>
This script is designed to be run as a webserver alternative to `asisten_py`.<br>
For Windows PowerShell, you can run this script using the command line `uvicorn asisten_app:build_app_from_env --factory --reload`<br>
Current available endpoints:<br>
- `/perangkat`: Returns all the item information stored in `DEVICES` variable in `aturan.py`.<br>
- `/peminjaman`: Returns the record of all borrowed item stored in `peminjaman.db`.<br>
- `/chat`: Send a POST request to interact with the agent.<br>
- `/konfirmasi`: Send a POST request to approve or reject the final confirmation to some specific query that the user may ask in `/chat`.
Currently, the only interaction required this sort of confirmation is if the user queries a request to borrow a device officially so that a record
will be recorded in `peminjaman.db`.<br> 


Note:<br>
This project has been tested with Python 3.12<br>
Dependencies required can be found in the file `requirements.txt`<br>
Rename the file `.env.example` to `.env` and fill in OPENROUTER_API_KEY with your actual api key<br>
You may change the AI model with a different one that's available in OpenRouter by changing the value of OPENROUTER_MODEL<br>
Currently the only accepted AGEN value in `.env` is `langchain`<br>


Changelog:<br>
- Version 3<br>
Added a webserver variant for `asisten.py` called `asisten_app.py`.<br>
The script `asisten.app.py` is created to be as agent/framework neutral as possible, with other framework designed to be slotted in such as `agen_langchain.py`.<br>
A new field in `.env.example` called `AGEN` is added with the only value available/accepted right now to be `langchain`.<br>
Added a new tool for the agent to allow users to officially borrow a device and leave a record in the database.<br>

- Version 2.5<br>
Renamed `PSEUDO_DB` to `DEVICES` for better representation.<br>
Added `coba_api.py`.<br>

- Version 2<br>
Added `penyimpanan.py`. This module deals with all the sql queries.<br>
Added `tools.py`. Moved all the @tools here.<br>
Added the function pinjam() to `aturan.py`. This allows one to "borrow" a device listed in `PSEUDO_DB` and leave a record in the SQLite database `peminjaman.db`.<br>

- Version 1.5<br>
Added `coba_sqlite.py`.<br>

- Version 1<br>
Added `cek_model.py`, `aturan.py`, and `assistent.py`.<br>
Added `test_aturan.py` to be used with pytest.<br>