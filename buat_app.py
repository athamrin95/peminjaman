from datetime import datetime
import os
from contextlib import asynccontextmanager
from typing import Any
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from langchain.agents import AgentState, create_agent
from langchain.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import HumanInTheLoopMiddleware, Runtime, before_model
from langchain_core.runnables import RunnableConfig
from langchain_core.messages.utils import trim_messages
from langchain.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.types import Command
from pydantic import BaseModel
from aturan import DB_PATH, DEVICES
from penyimpanan import get_records, setup_table
from tools import ALL_TOOLS, check_borrow_conditions


MAX_MESSAGE_ROUND = 6 # How many previous rounds of user queries -> agent response you want to keep.

def check_env(api_key:str, base_url:str, model:str) -> str | None:
    """Returns None if .env is loaded properly and the necessary properties are present."""
    if any(value is None or value == "" for value in(api_key, base_url, model)):
        return "OPENAI_API_KEY, OPENAI_BASE_URL, and/or OPENAI_MODEL is missing or cannot be read from your .env file. Exiting..."
    else:
        return None

@before_model
def trim_messages(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the .env properties first
    load_dotenv()
    result = check_env(os.getenv("OPENAI_API_KEY"), os.getenv("OPENAI_BASE_URL"), os.getenv("OPENAI_MODEL"))
    if result:
        raise RuntimeError(result)
    
    # Specify the model and create the agent
    model = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
    )
    system_prompt = f"""
    Today's date is {datetime.now().date()}
    Give your answer in Bahasa Indonesia.
    Only use the tool to find devices potentially stored in the database, not for every one of the user's query.
    Present your findings from the tools as-is, do not invent non-existent results.
    If nothing is found from using the tools, then simply inform the user that whatever they are requesting for is not found.
    """
    app.state.agent = create_agent(
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
        checkpointer=InMemorySaver()
    )

    # Setup the database if it doesn't exist
    setup_table(DB_PATH)
    
    yield


class ChatPayload(BaseModel):
    session_id: str
    query: str

class ConfirmationPayload(BaseModel):
    session_id: str
    interrupt_id: str
    confirmation: bool

app = FastAPI(lifespan=lifespan)

@app.get("/perangkat")
def devices():
    return DEVICES

@app.get("/peminjaman")
def check_borrowed_devices(tanggal: str | None = None):
    if tanggal is not None:
        try:
            datetime.strptime(tanggal, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail=f"The given date {tanggal} must follow the format YYYY-MM-DD!")

    return get_records(DB_PATH, tanggal)

@app.post("/chat")
def chat(payload: ChatPayload, request: Request):
    clean_session_id = payload.session_id.strip()
    clean_query = payload.query.strip()
    if not clean_session_id:
        raise HTTPException(status_code=400, detail="Empty session_id!")
    if not clean_query:
        raise HTTPException(status_code=400, detail="Empty query!")

    config: RunnableConfig = {"configurable": {"thread_id": clean_session_id}}
    response = request.app.state.agent.invoke(
        {"messages": [HumanMessage(content=clean_query)]},
        config=config,
        version="v2",
    )

    interrupt_list = []
    for interrupt in response.interrupts:
        interrupt_list.append({"id":interrupt.id, "text": interrupt.value})

    return {
        "answer": response.value["messages"][-1].text if response.value["messages"][-1].text != "" else None,
        "confirmation": interrupt_list if interrupt_list else None,
    }

@app.post("/konfirmasi")
def confirmation(payload: ConfirmationPayload, request: Request):
    clean_session_id = payload.session_id.strip()
    clean_interrupt_id = payload.interrupt_id.strip()
    clean_confirmation = payload.confirmation
    if not clean_session_id:
        raise HTTPException(status_code=400, detail="Empty session_id!")
    if not clean_interrupt_id:
        raise HTTPException(status_code=400, detail="Empty interrupt_id!")
    if not isinstance(clean_confirmation, bool):
        raise HTTPException(status_code=400, detail="Confirmation must be true or false!")

    decision = {}
    if payload.confirmation:
        decision[clean_interrupt_id] = {"type": "approve"}
    else:
        decision[clean_interrupt_id] = {"type": "reject", "message": "User rejected the confirmation."}

    config: RunnableConfig = {"configurable": {"thread_id": clean_session_id}}
    response = request.app.state.agent.invoke(
        Command(resume=decision),
        config=config,
        version="v2",
    )

    interrupt_list = []
    for interrupt in response.interrupts:
        interrupt_list.append({"id":interrupt.id, "text": interrupt.value})

    return {
        "answer": response.value["messages"][-1].text if response.value["messages"][-1].text != "" else None,
        "confirmation": interrupt_list if interrupt_list else None,
    }