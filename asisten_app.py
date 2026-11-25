from datetime import datetime
from contextlib import asynccontextmanager
import os
from typing import Any
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agen_langchain import create_agent_langchain_openai_openrouter, run_chat, run_confirmation
import agen_langchain
from aturan import DB_PATH, DEVICES
from penyimpanan import get_records, setup_table


class ChatPayload(BaseModel):
    session_id: str
    query: str

class ConfirmationPayload(BaseModel):
    session_id: str
    interrupt_id: str
    confirmation: bool

def build_app_from_env() -> FastAPI:
    """Factory function for `uvicorn asisten_app:buat_app_dari_env --factory --reload`."""
    load_dotenv()
    agent_env = os.getenv("AGEN", "")
    if not agent_env.strip():
        raise RuntimeError("AGEN is missing or empty in .env.")

    agent_string = agent_env.strip().lower()
    if agent_string == "langchain":
        agent = agen_langchain.create_agent_langchain_openai_openrouter()
        chat_runner = agen_langchain.run_chat
        confirmation_runner = agen_langchain.run_confirmation
    else:
        raise ValueError(f"Unsupported AGEN value: {agent_env}.")

    return build_app(agent, chat_runner, confirmation_runner)

def build_app(agent: Any, chat_runner: Any, confirmation_runner: Any) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.agent = agent
        app.state.run_chat = chat_runner
        app.state.run_confirmation = confirmation_runner
        setup_table(DB_PATH)
        yield

    app = FastAPI(lifespan=lifespan)
    app.state.agent = agent
    app.state.run_chat = chat_runner
    app.state.run_confirmation = confirmation_runner

    @app.get("/perangkat")
    def devices():
        return DEVICES

    @app.get("/peminjaman")
    def check_borrowed_devices(tanggal: str | None = None):
        if tanggal is not None:
            try:
                datetime.strptime(tanggal, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"The given date {tanggal} must follow the format YYYY-MM-DD!",
                )
        return get_records(DB_PATH, tanggal)

    @app.post("/chat")
    def chat(payload: ChatPayload):
        clean_session_id = payload.session_id.strip()
        clean_query = payload.query.strip()
        if not clean_session_id:
            raise HTTPException(status_code=400, detail="Empty session_id!")
        if not clean_query:
            raise HTTPException(status_code=400, detail="Empty query!")
        result = app.state.run_chat(app.state.agent, clean_session_id, clean_query)
        if "error" in result and "Exception error" in result.get("error"):
            raise HTTPException(status_code=502, detail="Encountered errors from the AI agent side!")
        return result

    @app.post("/konfirmasi")
    def confirmation(payload: ConfirmationPayload):
        clean_session_id = payload.session_id.strip()
        clean_interrupt_id = payload.interrupt_id.strip()
        clean_confirmation = payload.confirmation
        if not clean_session_id:
            raise HTTPException(status_code=400, detail="Empty session_id!")
        if not clean_interrupt_id:
            raise HTTPException(status_code=400, detail="Empty interrupt_id!")
        if not isinstance(clean_confirmation, bool):
            raise HTTPException(status_code=400, detail="Confirmation must be true or false!")

        result = app.state.run_confirmation(app.state.agent, clean_session_id, clean_interrupt_id, clean_confirmation)
        if result is None:
            raise HTTPException(status_code=404, detail="Interrupt not found!")
        if "error" in result and "Exception error" in result.get("error"):
            raise HTTPException(status_code=502, detail="Encountered errors from the AI agent side!")
        return result

    return app