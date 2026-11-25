from datetime import datetime
import os
from typing import Any
from dotenv import load_dotenv
from langchain.agents import AgentState, create_agent
from langgraph.errors import GraphRecursionError
from langchain.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import HumanInTheLoopMiddleware, Runtime, before_model
from langchain_core.runnables import RunnableConfig
from langchain_core.messages.utils import trim_messages
from langchain.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.types import Command
from tools import ALL_TOOLS, check_borrow_conditions


MAX_MESSAGE_ROUND = 6 # How many previous rounds of user queries -> agent response you want to keep.
RECURSION_LIMIT = 10 # Amount of time agent can keep invoking tool calls repeatedly

def check_env(api_key:str, base_url:str, model:str) -> str | None:
    """Returns None if .env is loaded properly and the necessary properties are present."""
    if any(value is None or value == "" for value in(api_key, base_url, model)):
        return "OPENROUTER_API_KEY, OPENROUTER_BASE_URL, and/or OPENAI_MODEL is missing or cannot be read from your .env file. Exiting..."
    else:
        return None

@before_model
def trim_messages(state: AgentState, runtime: Runtime) -> dict | None:
    """Keep only the last few rounds of messages as stated in MAX_MESSAGE_ROUND to fit context window."""
    messages = state["messages"]
    humanmessage_index_list = [
        i for i, msg in enumerate(messages) if isinstance(msg, HumanMessage)
    ]

    if len(humanmessage_index_list) <= MAX_MESSAGE_ROUND + 1:
        return None

    # Cut-off the excess messages
    new_messages = messages[humanmessage_index_list[-MAX_MESSAGE_ROUND - 1]:]
    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *new_messages
        ]
    }

def run_chat(agent: Any, session_id: str, query: str) -> dict:
    config: RunnableConfig = {"configurable": {"thread_id": session_id}, "recursion_limit": RECURSION_LIMIT}
    # Check if interrupt exist before doing anything else
    state = agent.get_state(config)
    if state is not None:
        interrupt_list = []
        for task in state.tasks:
            for interrupt in task.interrupts:
                interrupt_list.append({"id": interrupt.id, "text": interrupt.value})
        if interrupt_list:
            return {"answer": None, "confirmation": interrupt_list}
    try:
        response = agent.invoke(
            {"messages": [HumanMessage(content=query)]},
            config=config,
            version="v2",
        )
    except GraphRecursionError:
        return {
            "answer": "Sorry but the query is too complex for us to process all at once. Please simplify your query.",
            "confirmation": None,
        }
    except Exception as e:
        # e should be logged somewhere and not displayed back
        return {"error": "Exception error caught!"}

    interrupt_list = []
    for interrupt in response.interrupts:
        interrupt_list.append({"id": interrupt.id, "text": interrupt.value})
    return {
        "answer": response.value["messages"][-1].text if response.value["messages"][-1].text != "" else None,
        "confirmation": interrupt_list if interrupt_list else None,
    }

def run_confirmation(agent: Any, session_id: str, interrupt_id: str, approved: bool,) -> dict:
    config: RunnableConfig = {"configurable": {"thread_id": session_id}, "recursion_limit": RECURSION_LIMIT}
    # Check if interrupt exist given the interrupt id
    state = agent.get_state(config)
    if state is None:
        return None
    found_interrupt = False
    for task in state.tasks:
        for interrupt in task.interrupts:
            if interrupt.id == interrupt_id:
                found_interrupt = True
    if not found_interrupt:
        return None

    decision = {}
    if approved:
        decision[interrupt_id] = {"type": "approve"}
    else:
        decision[interrupt_id] = {
            "type": "reject",
            "message": "User rejected the confirmation. Do not proceed unless the user explicitly asks for it.",
        }
    try:
        response = agent.invoke(
            Command(resume=decision),
            config=config,
            version="v2",
        )
    except GraphRecursionError:
        return {
            "answer": "Sorry but the confirmation process is too complex for us to run all at once.",
            "confirmation": None,
        }
    except Exception as e:
        # e should be logged somewhere and not displayed back
        return {"error": "Exception error caught!"}
    
    interrupt_list = []
    for interrupt in response.interrupts:
        interrupt_list.append({"id": interrupt.id, "text": interrupt.value})
    return {
        "answer": response.value["messages"][-1].text if response.value["messages"][-1].text != "" else None,
        "confirmation": interrupt_list if interrupt_list else None,
    }


def create_agent_langchain_openai_openrouter() -> Any:
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENROUTER_BASE_URL")
    model_name = os.getenv("OPENAI_MODEL")

    env_error = check_env(api_key, base_url, model_name)
    if env_error:
        raise RuntimeError(env_error)

    model = ChatOpenAI(
        model=model_name,
        openai_api_key=api_key,
        base_url=base_url,
    )
    system_prompt = f"""
    Today's date is {datetime.now().date()}
    Give your answer in Bahasa Indonesia.
    Only use the tool to find devices potentially stored in the database, not for every one of the user's query.
    Present your findings from the tools as-is, do not invent non-existent results.
    If nothing is found from using the tools, then simply inform the user that whatever they are requesting for is not found.
    """
    return create_agent(
        model=model,
        tools=ALL_TOOLS,
        system_prompt=system_prompt,
        middleware=[
            trim_messages,
            HumanInTheLoopMiddleware(
                interrupt_on={
                    "borrow_a_device": {
                        "allowed_decisions": ["approve", "reject"],
                        "when": check_borrow_conditions,
                    },
                },
                interrupt_mode="per_call",
            ),
        ],
        checkpointer=InMemorySaver(),
    )