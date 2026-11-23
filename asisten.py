import os
import sys
from typing import Any
from dotenv import load_dotenv
from langchain.agents import AgentState, create_agent
from langchain.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import Runtime, before_model
from langchain_core.runnables import RunnableConfig
from langchain_core.messages.utils import trim_messages
from langchain.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from aturan import DB_PATH, DEVICES
from penyimpanan import setup_table
from tools import ALL_TOOLS


MAX_MESSAGE_ROUND = 6 # How many rounds of user queries -> answer response from the agent you want to keep
MESSAGE_LEN_LIST = []
PREV_MESSAGE_LEN = 0

def check_env(api_key:str, base_url:str, model:str) -> str:
    """Returns None if .env is loaded properly and the necessary properties are present."""
    if any(value is None or value == "" for value in(api_key, base_url, model)):
        return "OPENAI_API_KEY, OPENAI_BASE_URL, and/or OPENAI_MODEL is missing or cannot be read from your .env file. Exiting..."
    else:
        return None

def local_command(user_input:str):
    user_input = user_input[1:].casefold()
    
    if user_input == "keluar":
        print("Exiting...")
        sys.exit(1)
    elif user_input == "perangkat":
        for entry in DEVICES:
            print(f"Code: {entry['code']}; Name: {entry['name']}; Type: {entry['type']}.")
    else:
        print("Local command not recognized!")

@before_model
def trim_messages(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """Keep only the last few rounds of messages as stated in var MAX_MESSAGE_ROUND to fit context window."""
    messages = state["messages"]
    
    if len(MESSAGE_LEN_LIST) <= MAX_MESSAGE_ROUND:
        return None  
    
    count = MESSAGE_LEN_LIST.pop(0)
    new_messages = messages[count:]
    global PREV_MESSAGE_LEN; PREV_MESSAGE_LEN = len(new_messages)
    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *new_messages
        ]
    }

def main() -> None:
    # Load the .env properties first
    load_dotenv()
    result = check_env(os.getenv("OPENAI_API_KEY"), os.getenv("OPENAI_BASE_URL"), os.getenv("OPENAI_MODEL"))
    if result:
        print(result)
        sys.exit(1)

    # Specify the model and create the agent
    model = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        use_responses_api=True
    )
    system_prompt = """
    Give your answer in Bahasa Indonesia.
    Only use the tool to find devices potentially stored in the database, not for every one of the user's query.
    Present your findings from the tools as-is, do not invent non-existent results.
    If nothing is found from using the tools, then simply inform the user that whatever they are requesting for is not found.
    """
    agent = create_agent(
        model=model,
        tools=ALL_TOOLS,
        system_prompt=system_prompt,
        middleware=[trim_messages],
        checkpointer=InMemorySaver()
    )
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    # Setup the database if it doesn't exist
    setup_table(DB_PATH)

    # Chat session until user types "/keluar"
    global PREV_MESSAGE_LEN
    while True:
        user_input = input("Please type your query: ").strip()
        
        if user_input == "":
            print("You've entered an empty query, please try again!")
        elif user_input[0] == "/":
            local_command(user_input)
        else:
            response = agent.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config, 
            )
            new_message_len = len(response['messages']) - PREV_MESSAGE_LEN
            MESSAGE_LEN_LIST.append(new_message_len)
            PREV_MESSAGE_LEN = len(response['messages'])

            print(f"Agent answer: {response['messages'][-1].text}")
            print(f"Usage metadata: {response['messages'][-1].usage_metadata}")
        print()

if __name__ == "__main__":
    main()