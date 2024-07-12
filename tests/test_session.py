import pytest
import asyncio
from datetime import datetime, timezone
import os
from uuid import uuid4
from linedify.session import ConversationSession, ConversationSessionStore


def test_conversation_session():
    now = datetime.now(timezone.utc)
    session = ConversationSession("user_id", "conversation_id", now)

    assert session.user_id == "user_id"
    assert session.conversation_id == "conversation_id"
    assert session.updated_at == now

    session_dict = session.to_dict()
    session_dict["user_id"] == session.user_id
    session_dict["conversation_id"] == session.conversation_id
    session_dict["updated_at"] == now.isoformat()

    session2 = ConversationSession.from_dict(session_dict)
    assert session2.user_id == session.user_id
    assert session2.conversation_id == session.conversation_id
    assert session2.updated_at == session.updated_at


@pytest.mark.asyncio
async def test_conversation_session_store():
    store = ConversationSessionStore("sqlite:///test_sessions.db", 3)
    assert str(store.engine.url) == "sqlite:///test_sessions.db"
    assert store.timeout == 3.0

    # New session
    session = await store.get_session("user_id")
    assert session.user_id == "user_id"
    assert session.conversation_id is None
    assert isinstance(session.updated_at, datetime)

    last_updated_at = session.updated_at
    conversation_id = str(uuid4())
    session.conversation_id = conversation_id
    await store.set_session(session)

    # Successive session
    session2 = await store.get_session("user_id")
    assert session2.user_id == "user_id"
    assert session2.conversation_id == conversation_id
    assert session2.updated_at > last_updated_at

    last_updated_at = session2.updated_at
    await store.set_session(session2)

    await asyncio.sleep(store.timeout + 1.0)

    # Timeout
    session3 = await store.get_session("user_id")
    assert session3.user_id == "user_id"
    assert session3.conversation_id is None
    assert session3.updated_at > last_updated_at

    conversation_id3 = str(uuid4())
    session3.conversation_id = conversation_id3
    await store.set_session(session3)

    # Successive with another conversation_id
    session4 = await store.get_session("user_id")
    assert session4.user_id == "user_id"
    assert session4.conversation_id == conversation_id3

    # List sessions
    sessions = await store.get_user_conversations("user_id")

    assert sessions[-2].user_id == "user_id"
    assert sessions[-2].conversation_id == conversation_id
    assert sessions[-1].user_id == "user_id"
    assert sessions[-1].conversation_id == conversation_id3
    assert sessions[-1].updated_at > sessions[-2].updated_at
