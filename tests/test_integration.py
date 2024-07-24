import pytest
import os
from linebot.models import TextMessage, ImageMessage, StickerMessage, LocationMessage
from linedify import LineDify, DifyType


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


@pytest.mark.asyncio
async def test_make_inputs(line_dify):
    # TODO: Make test for handle_message_event

    def make_inputs(session):
        if not session.conversation_id:
            return {"foo": "bar"}
        else:
            return {}

    line_dify.make_inputs = make_inputs

    session = await line_dify.conversation_session_store.get_session("user_id")
    inputs = line_dify.make_inputs(session)
    assert inputs.get("foo") == "bar"

    session.conversation_id = "1234567890"
    inputs = line_dify.make_inputs(session)
    assert inputs.get("foo") is None
