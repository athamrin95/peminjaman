from __future__ import annotations

from typing import Any
from fastapi.testclient import TestClient
import pytest
import asisten_app


class FakeBorrowAgent:
    scripted_responses: list[dict[str, Any]] = []
    chat_calls: list[dict[str, str]] = []
    confirmation_calls: list[dict[str, Any]] = []
    # Tracks active interrupts per session_id: {session_id: {interrupt_id: interrupt_dict}}
    pending_interrupts: dict[str, dict[str, dict[str, Any]]] = {}   

    def queue_response(self, response: dict[str, Any]) -> None:
        self.scripted_responses.append(response)

    def pop_response(self) -> dict[str, Any]:
        if not self.scripted_responses:
            raise AssertionError("FakeBorrowAgent ran out of scripted responses.")
        return self.scripted_responses.pop(0)

    def run_chat(self, session_id: str, query: str) -> dict[str, Any]:
        self.chat_calls.append({"session_id": session_id, "query": query})
        resp = self.pop_response()

        confirmations = resp.get("confirmation") or []
        if confirmations:
            self.pending_interrupts.setdefault(session_id, {})
            for item in confirmations:
                self.pending_interrupts[session_id][item["id"]] = item
        return resp

    def run_confirmation(self, session_id: str, interrupt_id: str, confirmation: bool) -> dict[str, Any] | None:
        self.confirmation_calls.append(
            {
                "session_id": session_id,
                "interrupt_id": interrupt_id,
                "confirmation": confirmation,
            }
        )
        session_interrupts = self.pending_interrupts.get(session_id, {})
        if interrupt_id not in session_interrupts:
            return None

        resp = self.pop_response()
        # Clear resolved interrupt unless a new confirmation is returned
        session_interrupts.pop(interrupt_id, None)
        if not session_interrupts:
            self.pending_interrupts.pop(session_id, None)

        new_confirmations = resp.get("confirmation") or []
        if new_confirmations:
            self.pending_interrupts.setdefault(session_id, {})
            for item in new_confirmations:
                self.pending_interrupts[session_id][item["id"]] = item
        return resp


@pytest.fixture()
def fake_agent() -> FakeBorrowAgent:
    return FakeBorrowAgent()


@pytest.fixture()
def client(fake_agent: FakeBorrowAgent) -> TestClient:
    """Build FastAPI app wired to FakeBorrowAgent so /chat and /konfirmasi test HTTP contracts."""

    def fake_chat(agent: FakeBorrowAgent, session_id: str, query: str) -> dict[str, Any]:
        return agent.run_chat(session_id, query)

    def fake_confirmation(agent: FakeBorrowAgent, session_id: str, interrupt_id: str, approved: bool) -> dict[str, Any] | None:
        return agent.run_confirmation(session_id, interrupt_id, approved)

    app = asisten_app.build_app(fake_agent, fake_chat, fake_confirmation)
    with TestClient(app) as test_client:
        yield test_client


def test_borrow_a_device_chat_interrupt_and_approve_via_konfirmasi(client: TestClient, fake_agent: FakeBorrowAgent) -> None:
    """
    1. POST /chat triggers borrow_a_device interrupt and returns confirmation payload.
    2. POST /konfirmasi with confirmation=True completes the borrow and returns final answer.
    """
    interrupt_id = "123456"
    fake_agent.queue_response(
        {
            "answer": None,
            "confirmation": [
                {
                    "id": interrupt_id,
                    "text": {
                        "tool": "borrow_a_device",
                        "args": {
                            "device_code_name": "LP-01",
                            "borrower_name": "TestName",
                            "start_date": "2026-12-01",
                            "borrow_duration_in_days": 1,
                        },
                    },
                }
            ],
        }
    )
    fake_agent.queue_response(
        {
            "answer": "Peminjaman perangkat LP-01 atas nama TestName (2026-12-01 s.d. 2026-12-04) telah dikonfirmasi.",
            "confirmation": None,
        }
    )

    chat_res = client.post(
        "/chat",
        json={
            "session_id": "1",
            "query": "Pinjam LP-01 atas nama Andi mulai 2026-12-01 selama 3 hari",
        },
    )
    assert chat_res.status_code == 200
    chat_body = chat_res.json()
    assert chat_body["answer"] is None
    assert isinstance(chat_body["confirmation"], list)
    assert len(chat_body["confirmation"]) == 1
    assert chat_body["confirmation"][0]["id"] == interrupt_id

    confirm_res = client.post(
        "/konfirmasi",
        json={
            "session_id": "1",
            "interrupt_id": interrupt_id,
            "confirmation": True,
        },
    )
    assert confirm_res.status_code == 200
    confirm_body = confirm_res.json()
    assert confirm_body["confirmation"] is None
    assert "LP-01" in confirm_body["answer"]
    assert "TestName" in confirm_body["answer"]

    assert fake_agent.confirmation_calls == [
        {
            "session_id": "1",
            "interrupt_id": interrupt_id,
            "confirmation": True,
        }
    ]


def test_borrow_a_device_chat_interrupt_and_reject_via_konfirmasi(client: TestClient, fake_agent: FakeBorrowAgent) -> None:
    """
    1. POST /chat triggers borrow_a_device interrupt.
    2. POST /konfirmasi with confirmation=False rejects the borrow cleanly.
    """
    interrupt_id = "123456"
    fake_agent.queue_response(
        {
            "answer": None,
            "confirmation": [
                {
                    "id": interrupt_id,
                    "text": {
                        "tool": "borrow_a_device",
                        "args": {
                            "device_code_name": "PR-01",
                            "borrower_name": "TestName",
                            "start_date": "2026-12-05",
                            "borrow_duration_in_days": 2,
                        },
                    },
                }
            ],
        }
    )
    fake_agent.queue_response(
        {
            "answer": "Konfirmasi peminjaman perangkat PR-01 dibatalkan.",
            "confirmation": None,
        }
    )

    chat_res = client.post(
        "/chat",
        json={
            "session_id": "1",
            "query": "Saya mau pinjam PR-01 untuk TestName mulai 2026-12-05 selama 2 hari",
        },
    )
    assert chat_res.status_code == 200
    returned_id = chat_res.json()["confirmation"][0]["id"]
    assert returned_id == interrupt_id

    confirm_res = client.post(
        "/konfirmasi",
        json={
            "session_id": "1",
            "interrupt_id": interrupt_id,
            "confirmation": False,
        },
    )
    assert confirm_res.status_code == 200
    confirm_body = confirm_res.json()
    assert confirm_body["confirmation"] is None
    assert "dibatalkan" in confirm_body["answer"].lower()