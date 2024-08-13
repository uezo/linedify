import json
from logging import getLogger, NullHandler
from traceback import format_exc
from typing import Dict, List, Tuple, Union

from linebot.v3 import WebhookParser
from linebot.v3.messaging import (
    Configuration,
    AsyncApiClient,
    AsyncMessagingApi,
    Message,
    TextMessage,
    ReplyMessageRequest
)
from linebot.v3.webhooks import (
    Event,
    MessageEvent,
    TextMessageContent,
    StickerMessageContent,
    LocationMessageContent,
    ImageMessageContent
)

from .dify import DifyAgent, DifyType
from .session import ConversationSession, ConversationSessionStore


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
        session_db_url: str = "sqlite:///sessions.db",
        session_timeout: float = 3600.0,
        verbose: bool = False
    ) -> None:

        self.verbose = verbose

        # LINE
        line_api_configuration = Configuration(
            access_token=line_channel_access_token
        )
        self.line_api_client = AsyncApiClient(line_api_configuration)
        self.line_api = AsyncMessagingApi(self.line_api_client)
        self.webhook_parser = WebhookParser(line_channel_secret)

        self._validate_event = self.validate_event_default
        self._event_handlers = {
            "message": self.handle_message_event
        }
        self._default_event_handler = self.event_handler_default
        self._message_parsers = {
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

        self._make_inputs = self.make_inputs_default
        self._to_reply_message = self.to_reply_message_default
        self._to_error_message = self.to_error_message_default

    # Decorators
    def event(self, event_type=None):
        def decorator(func):
            if event_type is None:
                self._default_event_handler = func
            else:
                self._event_handlers[event_type] = func
            return func
        return decorator

    def parse_message(self, message_type):
        def decorator(func):
            self._message_parsers[message_type] = func
            return func
        return decorator

    def validate_event(self, func):
        self._validate_event = func
        return func

    def make_inputs(self, func):
        self._make_inputs = func
        return func

    def to_reply_message(self, func):
        self._to_reply_message = func
        return func

    def to_error_message(self, func):
        self._to_error_message = func
        return func

    # Processors
    async def process_request(self, request_body: str, signature: str):
        events = self.webhook_parser.parse(request_body, signature)
        for event in events:
            reply_messages = await self.process_event(event)

            try:
                if reply_messages and hasattr(event, "reply_token"):
                    await self.line_api.reply_message(
                        ReplyMessageRequest(
                            replyToken=event.reply_token,
                            messages=reply_messages
                        )
                    )

            except Exception as eex:
                logger.error(f"Error at replying error message for event: {eex}\n{format_exc()}")

    async def process_event(self, event: Event):
        try:
            if validation_messages := await self._validate_event(event):
                return validation_messages
            
            else:
                event_handler = self._event_handlers.get(event.type)
                if event_handler:
                    return await event_handler(event)
                else:
                    return await self._default_event_handler(event)

        except Exception as ex:
            logger.error(f"Error at process_event: {ex}\n{format_exc()}")
            return await self._to_error_message(event, ex)

    # Event handlers
    async def handle_message_event(self, event: MessageEvent):
        conversation_session = None
        try:
            if self.verbose:
                logger.info(f"Request from LINE: {json.dumps(event.as_json_dict(), ensure_ascii=False)}")

            parse_message = self._message_parsers.get(event.message.type)
            if not parse_message:
                raise Exception(f"Unhandled message type: {event.message.type}")

            request_text, image_bytes = await parse_message(event.message)
            conversation_session = await self.conversation_session_store.get_session(event.source.user_id)
            inputs = await self._make_inputs(conversation_session)

            conversation_id, text, data = await self.dify_agent.invoke(
                conversation_session.conversation_id,
                text=request_text,
                image=image_bytes,
                inputs=inputs
            )

            conversation_session.conversation_id = conversation_id
            await self.conversation_session_store.set_session(conversation_session)

            response_messages = await self._to_reply_message(text, data, conversation_session)

            if self.verbose:
                logger.info(f"Response to LINE: {', '.join([json.dumps(m.as_json_dict(), ensure_ascii=False) for m in response_messages])}")

            return response_messages

        except Exception as ex:
            logger.error(f"Error at handle_message_event: {ex}\n{format_exc()}")

            try:
                error_message = await self._to_error_message(event, ex, conversation_session)
                return error_message

            except Exception as eex:
                logger.error(f"Error at replying error message for message event: {eex}\n{format_exc()}")

    async def event_handler_default(self, event: Event):
        logger.warning(f"Unhandled event type: {event.type}")

    # Message parsers
    async def parse_text_message(self, message: TextMessageContent) -> Tuple[str, bytes]:
        return message.text, None

    async def parse_image_message(self, message: ImageMessageContent) -> Tuple[str, bytes]:
        image_stream = await self.line_api.get_message_content(message.id)
        image_bytes = bytearray()
        async for chunk in image_stream.iter_content():
            image_bytes.extend(chunk)
        return "", image_bytes

    async def parse_sticker_message(self, message: StickerMessageContent) -> Tuple[str, bytes]:
        sticker_keywords = ", ".join([k for k in message["keywords"]])
        return f"You received a sticker from user in messenger app: {sticker_keywords}", None

    async def parse_location_message(self, message: LocationMessageContent) -> Tuple[str, bytes]:
        return f"You received a location info from user in messenger app:\n    - address: {message['address']}\n    - latitude: {message['latitude']}\n    - longitude: {message['longitude']}", None

    # Defaults
    async def validate_event_default(self, Event) -> Union[None, List[Message]]:
        return None

    async def make_inputs_default(self, session: ConversationSession) -> Dict:
        return {}

    async def to_reply_message_default(self, text: str, data: dict, session: ConversationSession) -> List[Message]:
        return [TextMessage(text=text)]

    async def to_error_message_default(self, event: Event, ex: Exception, session: ConversationSession = None) -> List[Message]:
        return [TextMessage(text="Error 🥲")]

    # Application lifecycle
    async def shutdown(self):
        await self.line_api_client.close()
