import json
from logging import getLogger, NullHandler
from traceback import format_exc
from typing import List, Tuple
import aiohttp
from linebot import AsyncLineBotApi, WebhookParser
from linebot.aiohttp_async_http_client import AiohttpAsyncHttpClient
from linebot.models import (
    Event, MessageEvent,
    TextMessage, StickerMessage, LocationMessage,
    ImageMessage, SendMessage, TextSendMessage
)
from .dify import DifyAgent, DifyType
from .session import ConversationSessionStore


logger = getLogger(__name__)
logger.addHandler(NullHandler())


class LineDifyIntegrator:
    def __init__(self, *,
        line_channel_access_token: str,
        line_channel_secret: str,
        dify_api_key: str,
        dify_base_url: str,
        dify_user: str,
        dify_type: DifyType = DifyType.Agent,
        error_response: str = None,
        session_db_url: str = "sqlite:///sessions.db",
        session_timeout: float = 3600.0,
        verbose: bool = False
    ) -> None:

        self.verbose = verbose

        # LINE
        self.line_api_session = aiohttp.ClientSession()
        client = AiohttpAsyncHttpClient(self.line_api_session)
        self.line_api = AsyncLineBotApi(
            channel_access_token=line_channel_access_token,
            async_http_client=client
        )
        self.webhook_parser = WebhookParser(channel_secret=line_channel_secret)
        self.message_parsers = {
            "text": self.parse_text_message,
            "image": self.parse_image_message,
            "sticker": self.parse_sticker_message,
            "location": self.parse_location_message
        }

        self.conversation_session_store = ConversationSessionStore(
            db_url=session_db_url,
            timeout=session_timeout
        )

        # Dify
        self.dify_agent = DifyAgent(
            api_key=dify_api_key,
            base_url=dify_base_url,
            user=dify_user,
            type=dify_type,
            verbose=self.verbose
        )

        # Custom logics
        self.validate_event = None
        self.make_inputs = None

        self.error_response = error_response

    async def process_request(self, request_body: str, signature: str):
        events = self.webhook_parser.parse(request_body, signature)
        for event in events:
            await self.process_event(event)

    async def process_event(self, event: Event):
        try:
            if event.type == "message":
                await self.handle_message_event(event)
            else:
                await self.handle_event(event)
        except Exception as ex:
            logger.error(f"Error at process_event: {ex}\n{format_exc()}")

    async def parse_text_message(self, message: TextMessage) -> Tuple[str, bytes]:
        return message.text, None

    async def parse_image_message(self, message: ImageMessage) -> Tuple[str, bytes]:
        image_stream = await self.line_api.get_message_content(message.id)
        image_bytes = bytearray()
        async for chunk in image_stream.iter_content():
            image_bytes.extend(chunk)
        return "", image_bytes

    async def parse_sticker_message(self, message: StickerMessage) -> Tuple[str, bytes]:
        sticker_keywords = ", ".join([k for k in message["keywords"]])
        return f"You received a sticker from user in messenger app: {sticker_keywords}", None

    async def parse_location_message(self, message: LocationMessage) -> Tuple[str, bytes]:
        return f"You received a location info from user in messenger app:\n    - address: {message['address']}\n    - latitude: {message['latitude']}\n    - longitude: {message['longitude']}", None

    async def make_error_response(self, event: MessageEvent, ex: Exception) -> List[SendMessage]:
        return [TextSendMessage(text=self.error_response or "Error 🥲")]

    async def handle_message_event(self, event: MessageEvent):
        try:
            if self.verbose:
                logger.info(f"Request from LINE: {json.dumps(event.as_json_dict(), ensure_ascii=False)}")

            if self.validate_event:
                validation_message = await self.validate_event(event)
                if validation_message:
                    await self.line_api.reply_message(event.reply_token, [validation_message])
                    return

            parse_message = self.message_parsers.get(event.message.type)
            if not parse_message:
                raise Exception(f"Unhandled message type: {event.message.type}")

            request_text, image_bytes = await parse_message(event.message)

            conversation_session = await self.conversation_session_store.get_session(event.source.user_id)
            if self.make_inputs:
                inputs = self.make_inputs(conversation_session)
            else:
                inputs = {}

            conversation_id, text, data = await self.dify_agent.invoke(conversation_session.conversation_id, text=request_text, image=image_bytes, inputs=inputs)
            conversation_session.conversation_id = conversation_id
            await self.conversation_session_store.set_session(conversation_session)

            response_messages = await self.process_response(text, data)

            if self.verbose:
                logger.info(f"Response to LINE: {', '.join([json.dumps(m.as_json_dict(), ensure_ascii=False) for m in response_messages])}")

            await self.line_api.reply_message(event.reply_token, response_messages)

        except Exception as ex:
            logger.error(f"Error at handle_message_event: {ex}\n{format_exc()}")

            try:
                error_response = await self.make_error_response(event, ex)
                await self.line_api.reply_message(event.reply_token, error_response)

            except Exception as eex:
                logger.error(f"Error at replying error message: {eex}\n{format_exc()}")

    async def handle_event(self, event: Event):
        logger.warning(f"Unhandled event type: {event.type}")

    async def process_response(self, text: str, data: dict) -> List[SendMessage]:
        return [TextSendMessage(text=text)]

    async def shutdown(self):
        await self.line_api_session.close()
