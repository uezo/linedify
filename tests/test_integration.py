import pytest
import json
import os
from linebot.v3.webhooks import MessageEvent, PostbackEvent, FollowEvent, ImageMessageContent, StickerMessageContent, LocationMessageContent, ContentProvider
from linebot.v3.messaging import TextMessage
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


def to_message_event(text: str) -> MessageEvent:
    json_dict = json.loads('{"deliveryContext": {"isRedelivery": false}, "message": {"id": "521033363122028567", "text": "", "type": "text", "quoteToken": "XXXXXX"}, "mode": "active", "replyToken": "7d34442b4f0c4f319f721ed6293fb70f", "source": {"type": "user", "userId": "U1234xx5f678x90x123456x78x9012xx3"}, "timestamp": 1723391389452, "type": "message", "webhookEventId": "01J5123C4954D0284W9KN11QCX"}')
    json_dict["message"]["text"] = text
    return MessageEvent.from_dict(json_dict)


def to_location_message_event() -> MessageEvent:
    json_dict = json.loads('{"deliveryContext": {"isRedelivery": false}, "message": {"address": "\u6771\u4eac\u90fd\u76ee\u9ed2\u533a\u81ea\u7531\u304c\u4e181\u4e01\u76ee9-8", "id": "521035897605456135", "latitude": 35.6075767, "longitude": 139.6690939, "title": "\u81ea\u7531\u304c\u4e18\u99c5\uff08\u6771\u6025\uff09", "type": "location"}, "mode": "active", "replyToken": "10047dd69f4b483f97c4d3aa13f0ce70", "source": {"type": "user", "userId": "U1234xx5f678x90x123456x78x9012xx3"}, "timestamp": 1723392900114, "type": "message", "webhookEventId": "01J513HFD69N3SD0SRAD16CZ8S"}')
    return MessageEvent.from_dict(json_dict)


def to_image_message_event() -> MessageEvent:
    json_dict = json.loads('{"deliveryContext": {"isRedelivery": false}, "message": {"address": "\u6771\u4eac\u90fd\u76ee\u9ed2\u533a\u81ea\u7531\u304c\u4e181\u4e01\u76ee9-8", "id": "521035897605456135", "latitude": 35.6075767, "longitude": 139.6690939, "title": "\u81ea\u7531\u304c\u4e18\u99c5\uff08\u6771\u6025\uff09", "type": "location"}, "mode": "active", "replyToken": "10047dd69f4b483f97c4d3aa13f0ce70", "source": {"type": "user", "userId": "U1234xx5f678x90x123456x78x9012xx3"}, "timestamp": 1723392900114, "type": "message", "webhookEventId": "01J513HFD69N3SD0SRAD16CZ8S"}')
    return MessageEvent.from_dict(json_dict)


def to_postback_event(data: str) -> PostbackEvent:
    json_dict = json.loads('{"replyToken": "b60d432864f44d079f6d8efe86cf404b","type": "postback","mode": "active","source": {"userId": "U91eeaf62d...","type": "user"},"timestamp": 1513669370317,"webhookEventId": "01FZ74A0TDDPYRVKNK77XKC3ZR","deliveryContext": {"isRedelivery": false},"postback": {"data": "","params": {"datetime": "2017-12-25T01:00"}}}')
    json_dict["postback"]["data"] = data
    return PostbackEvent.from_dict(json_dict)


def to_follow_event() -> FollowEvent:
    json_dict = json.loads('{"replyToken": "85cbe770fa8b4f45bbe077b1d4be4a36","type": "follow","mode": "active","timestamp": 1705891467176,"source": {"type": "user","userId": "U3d3edab4f36c6292e6d8a8131f141b8b"},"webhookEventId": "01HMQGW40RZJPJM3RAJP7BHC2Q","deliveryContext": {"isRedelivery": false},"follow": {"isUnblocked": false}}')
    return FollowEvent.from_dict(json_dict)


@pytest.mark.asyncio
async def test_validate_event(line_dify):
    @line_dify.validate_event
    async def validate_event(event):
        if hasattr(event, "reply_token"):
            if event.type == "message" and event.message.type == "text" and event.message.text == "invalid":
                return [TextMessage(text="invalid event")]

    reply_messages = await line_dify.process_event(to_message_event("hello"))
    assert reply_messages[0].text is not None
    assert reply_messages[0].text != ""
    assert reply_messages[0].text != "invalid event"

    reply_messages = await line_dify.process_event(to_message_event("invalid"))
    assert reply_messages[0].text == "invalid event"


@pytest.mark.asyncio
async def test_handle_events(line_dify):
    @line_dify.event("postback")
    async def handle_message_event(event):
        return [TextMessage(text=f"Response for postback event: {event.postback.data}")]

    @line_dify.event()
    async def handle_event(event):
        return [TextMessage(text=f"Response for event type: {event.type}")]

    # Default message event handler works
    reply_messages = await line_dify.process_event(to_message_event("say hello"))
    assert "hello" in reply_messages[0].text.lower()

    # Postback
    reply_messages = await line_dify.process_event(to_postback_event("foo=bar"))
    assert "foo=bar" in reply_messages[0].text

    # Follow
    reply_messages = await line_dify.process_event(to_follow_event())
    assert reply_messages[0].text == "Response for event type: follow"


@pytest.mark.asyncio
async def test_parse_messages(line_dify):
    @line_dify.parse_message("text")
    async def parse_text_message(message):
        return (f"「{message.text}」の対義語を答えてください", None)

    @line_dify.parse_message("location")
    async def parse_location_message(message):
        return (f"「{message.title}」は何区ですか？", None)

    reply_messages = await line_dify.process_event(to_message_event("明るい"))
    assert "暗い" in reply_messages[0].text

    reply_messages = await line_dify.process_event(to_location_message_event())
    assert "目黒" in reply_messages[0].text


@pytest.mark.skip("Not testable for now -> RuntimeError: Event loop is closed")
@pytest.mark.asyncio
async def test_parse_image_message(line_dify, image_bytes):
    image_url = "https://github.com/uezo/linedify/blob/main/tests/resources/catgirl.png?raw=true"
    image_message = ImageMessageContent(id="12345", contentProvider=ContentProvider(type="external", previewImageUrl=image_url, originalContentUrl=image_url), quoteToken="XXXXX")
    parsed_text, parsed_image = await line_dify.parse_image_message(image_message)
    assert parsed_text == ""
    assert parsed_image == image_bytes


@pytest.mark.asyncio
async def test_parse_sticker_message(line_dify):
    text_message = StickerMessageContent(id="123456", packageId="pkgid", stickerId="stkid", stickerResourceType="STATIC", text="Hello, world!", keywords=["fun", "happy"], quoteToken="XXXXX")
    parsed_text, parsed_image = await line_dify.parse_sticker_message(text_message)
    assert parsed_text == f"You received a sticker from user in messenger app: fun, happy"
    assert parsed_image is None


@pytest.mark.asyncio
async def test_parse_location_message(line_dify):
    text_message = LocationMessageContent(id="123456", text="Hello, world!", address="Jiyugaoka, Tokyo", latitude=35.6, longitude=139.6)
    parsed_text, parsed_image = await line_dify.parse_location_message(text_message)
    assert parsed_text == f"You received a location info from user in messenger app:\n    - address: Jiyugaoka, Tokyo\n    - latitude: 35.6\n    - longitude: 139.6"
    assert parsed_image is None


@pytest.mark.asyncio
async def test_format_request_text(line_dify):
    @line_dify.format_request_text
    async def format_request_text(request_text, image_bytes):
        return "「ニャー」と言ってください。それ以外絶対に何も言わないこと"

    reply_messages = await line_dify.process_event(to_message_event("ユーザーの好きな食べ物は？"))
    assert "ニャー" in reply_messages[0].text


@pytest.mark.asyncio
async def test_make_inputs(line_dify):
    @line_dify.make_inputs
    async def make_inputs(session):
        return {"favorite_food": "りんご"}

    await line_dify.conversation_session_store.expire_session("U1234xx5f678x90x123456x78x9012xx3")
    reply_messages = await line_dify.process_event(to_message_event("ユーザーの好きな食べ物は？"))
    assert "りんご" in reply_messages[0].text


@pytest.mark.asyncio
async def test_to_reply_message(line_dify):
    @line_dify.to_reply_message
    async def to_reply_message(text, data, session):
        reply_messages = await line_dify.to_reply_message_default(text, data, session)
        reply_messages.append(TextMessage(text="Additional message"))
        return reply_messages

    reply_messages = await line_dify.process_event(to_message_event("say hello"))
    assert "hello" in reply_messages[0].text.lower()
    assert reply_messages[1].text == "Additional message"


@pytest.mark.asyncio
async def test_to_error_message(line_dify):
    @line_dify.to_error_message
    async def to_error_message(event, ex, session = None):
        text = "Custom error message"
        return [TextMessage(text=text)]

    @line_dify.event("message")
    async def handle_message_event(event):
        raise

    reply_messages = await line_dify.process_event(to_message_event("hello"))
    assert reply_messages[0].text == "Custom error message"


@pytest.mark.asyncio
async def test_preserve_line_breaks(line_dify):
    captured = {}

    async def fake_invoke(*, conversation_id, text=None, image=None, inputs=None, user=None, start_as_new=False):
        captured["text"] = text
        return ("cid123", "first line\r\nsecond line", {})

    line_dify.dify_agent.invoke = fake_invoke

    reply_messages = await line_dify.process_event(to_message_event("first line\r\nsecond line"))

    assert captured["text"] == "first line\nsecond line"
    assert reply_messages[0].text == "first line\nsecond line"
