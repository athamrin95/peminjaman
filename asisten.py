import os
import sys
from typing import Any
from dotenv import load_dotenv
from langchain.agents import AgentState, create_agent
from langchain.messages import HumanMessage
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import Runtime, before_model
from langchain_core.runnables import RunnableConfig
from langchain_core.messages.utils import trim_messages
from langchain.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from aturan import cari_perangkat, PSEUDO_DB

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
        for entry in PSEUDO_DB:
            print(f"Code: {entry['code']}; Name: {entry['name']}; Type: {entry['type']}.")
    else:
        print("Local command not recognized!")

@tool
def find_devices(text:str):
    """Find device(s) from the database given the word/text argument"""
    return cari_perangkat(text)

@before_model
def trim_messages_middleware(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """Keep history trimmed safely using LangChain's built-in message counting."""
    messages = state["messages"]
    trimmed_messages = trim_messages(
        messages,
        max_tokens=6,
        strategy="last",
        start_on="human",
        include_system=False,
        token_counter=len,
    )
    if len(trimmed_messages) == len(messages):
        return None
    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *trimmed_messages
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
    If no device/match is found from find_devices, then inform the user that nothing is found.
    """
    agent = create_agent(
        model=model,
        tools=[find_devices],
        system_prompt=system_prompt,
        middleware=[trim_messages_middleware],
        checkpointer=InMemorySaver()
    )
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}

    # Chat session until user types "/keluar"
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
            print(f"Agent answer: {response['messages'][-1].text}")
            print(f"Usage metadata: {response['messages'][-1].usage_metadata}")
        print()

if __name__ == "__main__":
    main()