import pytest
import asyncio
import os
from datetime import datetime, timezone
from linebot.models import TextMessage, ImageMessage, StickerMessage, LocationMessage
from linedify import LineDify, DifyType
from linedify.integration import ConversationSession, ConversationSessionStore


@pytest.fixture
def line_dify():
    ld = LineDify(
        line_channel_access_token=os.environ.get("YOUR_CHANNEL_ACCESS_TOKEN"),
        line_channel_secret=os.environ.get("YOUR_CHANNEL_SECRET"),
        dify_api_key=os.environ.get("DIFY_API_KEY"),
        dify_base_url=os.environ.get("DIFY_BASE_URL"),
        dify_user=os.environ.get("DIFY_USER"),
        dify_type=DifyType.Agent
    )

    class AsyncIteratorWrapper:
        async def __aiter__(self):
            pass

        async def __anext__(self):
            pass

        async def iter_content(self):
            with open(os.environ.get("DIFY_IMAGE_PATH"), "rb") as image_file:
                while chunk := image_file.read(1024):
                    yield chunk

    async def get_message_content(id):
        return AsyncIteratorWrapper()

    ld.line_api.get_message_content = get_message_content
    return ld


@pytest.fixture
def image_bytes():
    with open(os.environ.get("DIFY_IMAGE_PATH"), 'rb') as image_file:
        return image_file.read()


@pytest.mark.asyncio
async def test_parse_text_message(line_dify):
    text_message = TextMessage(text="Hello, world!")
    parsed_text, parsed_image = await line_dify.parse_text_message(text_message)
    assert parsed_text == "Hello, world!"
    assert parsed_image is None


@pytest.mark.asyncio
async def test_parse_image_message(line_dify, image_bytes):
    image_message = ImageMessage(id="12345")
    parsed_text, parsed_image = await line_dify.parse_image_message(image_message)
    assert parsed_text == ""
    assert parsed_image == image_bytes


@pytest.mark.asyncio
async def test_parse_sticker_message(line_dify):
    text_message = StickerMessage(text="Hello, world!", keywords=["fun", "happy"])
    parsed_text, parsed_image = await line_dify.parse_sticker_message(text_message)
    assert parsed_text == f"You received a sticker from user in messenger app: fun, happy"
    assert parsed_image is None


@pytest.mark.asyncio
async def test_parse_text_message(line_dify):
    text_message = LocationMessage(text="Hello, world!", address="Jiyugaoka, Tokyo", latitude=35.6, longitude=139.6)
    parsed_text, parsed_image = await line_dify.parse_location_message(text_message)
    assert parsed_text == f"You received a location info from user in messenger app:\n    - address: Jiyugaoka, Tokyo\n    - latitude: 35.6\n    - longitude: 139.6"
    assert parsed_image is None


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
    store = ConversationSessionStore("test_sessions", 3)
    assert store.directory == "test_sessions"
    assert store.timeout == 3.0
    assert os.path.exists("test_sessions") is True

    # New session
    session = await store.get_session("user_id")
    assert session.user_id == "user_id"
    assert session.conversation_id is None
    assert isinstance(session.updated_at, datetime)

    last_updated_at = session.updated_at
    session.conversation_id = "conversation_id"
    await store.set_session(session)

    # Successive session
    session2 = await store.get_session("user_id")
    assert session2.user_id == "user_id"
    assert session2.conversation_id == "conversation_id"
    assert session2.updated_at > last_updated_at

    last_updated_at = session2.updated_at
    await store.set_session(session2)

    await asyncio.sleep(store.timeout + 1.0)

    # Timeout
    session3 = await store.get_session("user_id")
    assert session3.user_id == "user_id"
    assert session3.conversation_id is None
    assert session3.updated_at > last_updated_at
