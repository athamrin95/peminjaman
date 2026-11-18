This project showcases the ChatOpenAI class (LangChain integration wrapper for OpenAI's chat models).<br>

`cek_model.py`:<br>
This script simply checks if the code is working properly by sending/invoking a question to the AI and receiving a proper response from it.<br>

`asistent.py`:<br>
This script uses the LangChain agent framework to give the AI the necessary tool to execute user's query to find the requested item information from the
"database".<br>

Available local command:<br>
- `/keluar`: Exits the script.<br>
- `/perangkat`: Prints all the item information stored in the "database" locally.<br>


Note:<br>
This project has been tested with Python 3.12<br>
Dependencies required can be found in the file `requirements.txt`<br>
Rename the file `.env.example` to `.env` and fill in OPENROUTER_API_KEY with your actual api key<br>
You may change the AI model with a different one that's available in OpenRouter by changing the value of OPENROUTER_MODEL<br>