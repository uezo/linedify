# linedify

💬⚡ linedify: Supercharging your LINE Bot with Dify power!


## ✨ Features

- 🧩 Seamless Dify-LINE Bot Integration

    - Connect Dify with LINE Bot using minimal code
    - Build powerful and efficient chatbots in no time

- 📸 Rich Input Support

    - Handle images, location data, and stickers out of the box
    - Customize to work with LINE-specific UI like Flex Messages

- 🪄 Developer-Friendly

    - Built on FastAPI for high performance and easy scaling
    - Asynchronous processing for smooth operations
    - Compatible with Dify API v1.6.0 streaming events


## 📦 Install

```sh
pip install linedify
```


## 🚀 Quick Start

Make the following script as `run.py` as the handler for WebHook from LINE API server.

By passing the HTTP request body and signature to `line_dify.process_request`, the entire process from receiving user messages to calling Dify and responding to the user is executed.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, BackgroundTasks
from linedify import LineDify
import os

# LINE Bot - Dify Agent Integrator
line_dify = LineDify(
    line_channel_access_token=YOUR_CHANNEL_ACCESS_TOKEN,
    line_channel_secret=YOUR_CHANNEL_SECRET,
    dify_api_key=DIFY_API_KEY,
    dify_base_url=DIFY_BASE_URL,    # e.g. http://localhost/v1
    dify_user=DIFY_USER
)

TARGET_ROOM_ID = os.getenv("TARGET_ROOM_ID")

@line_dify.validate_event
async def validate_event(event):
    if TARGET_ROOM_ID and event.source.type == "room" and event.source.room_id != TARGET_ROOM_ID:
        return []

# FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await line_dify.shutdown()

app = FastAPI(lifespan=lifespan)

@app.post("/linebot")
async def handle_request(request: Request, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        line_dify.process_request,
        request_body=(await request.body()).decode("utf-8"),
        signature=request.headers.get("X-Line-Signature", "")
    )
    return "ok"
```

Start server.

```
uvicorn run:app
```

NOTE: You have to expose the host:port to where the LINE API server can access.

## 🔧 Environment Variables

Copy `.env.example` to `.env` and set the following variables:

- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_CHANNEL_SECRET`
- `DIFY_API_KEY`
- `DIFY_BASE_URL`
- `DIFY_USER`
- *(optional)* `DIFY_IMAGE_PATH` - path to an image file for tests
- *(optional)* `PORT` - server port (default `18080`)
- *(optional)* `TARGET_ROOM_ID` - room ID the bot responds to
- *(optional)* `LINEDIFY_VERBOSE` - set to `true` to enable verbose logging

## 🐳 Docker

Use the following commands to build and run the container image.

```sh
docker build -t linedify .
docker run -p 8443:8443 \
  -e LINE_CHANNEL_ACCESS_TOKEN=YOUR_CHANNEL_ACCESS_TOKEN \
  -e LINE_CHANNEL_SECRET=YOUR_CHANNEL_SECRET \
  -e DIFY_API_KEY=DIFY_API_KEY \
  -e DIFY_BASE_URL=DIFY_BASE_URL \
  -e DIFY_USER=DIFY_USER \
  -e TARGET_ROOM_ID=YOUR_ROOM_ID \
  -e LINEDIFY_VERBOSE=true \
  -e PORT=8443 \
  linedify
```

The default listening port is `18080`. To change it, override the `PORT` environment variable.
For example, to listen on port 8443, specify as follows.

```sh
PORT=8443
```



## 🕹️ Switching Types

linedify supports Agent and Chatbot for now. (You can add support for TextGenerator and Workflow on your own!)

You can switch the types by setting `dify_type` to the constructor of LineDify. Default is `DifyType.Agent`.

```python
line_dify = LineDify(
    line_channel_access_token=YOUR_CHANNEL_ACCESS_TOKEN,
    line_channel_secret=YOUR_CHANNEL_SECRET,
    dify_api_key=DIFY_API_KEY,
    dify_base_url=DIFY_BASE_URL,
    dify_user=DIFY_USER,
    dify_type=DifyType.Chatbot  # <- DifyType.Agent or DifyType.Chatbot
)
```


## 💎 Use UI Components

Implement function to edit reply message below the decorator `@line_dify.to_reply_message`.

```python
from typing import List
from linebot.v3.messaging import Message, TextMessage, QuickReply, QuickReplyItem, MessageAction
from linedify.session import ConversationSession

@line_dify.to_reply_message
async def to_reply_message(text: str, data: dict, session: ConversationSession) -> List[Message]:
    response_message = TextMessage(text=text)

    # Show QuickReply buttons when tool "reservation" was executed on Dify
    if tool := data.get("tool"):
        if tool == "reservation":
            response_message.quick_reply = QuickReply([
                QuickReplyItem(action=MessageAction(label="Checkout", text="Checkout")),
                QuickReplyItem(action=MessageAction(label="Cancel", text="Cancel"))
            ])

    return [response_message]
```

## 🎨 Custom Logic

### Event Validation

Use `@line_dify.validate_event` to validate event before handling.

```python
banned_users = ["U123456", "U234567"]

@line_dify.validate_event
async def validate_event(event):
    line_user_id = event.source.user_id
    if line_user_id in banned_users:
        # Return the list of TextMessage to reply immediately without processing the event
        return [TextMessage("Forbidden")]
```


### Handle events

Use `@line_dify.event(event_type)` to customize event handlers.

```python
# Add handler for Postback event
@line_dify.event("postback")
async def handle_message_event(event: PostbackEvent):
    # Do something here
    # Return reply messages
    return [TextMessage(f"Response for postback event: {event.postback.data}")]

# Add handler for unspecified event
@line_dify.event()
async def handle_event(event):
    # Do something here
    # Return reply messages
    return [TextMessage(f"Response for event type: {event.type}")]
```


### Parse messages

Use `@line_dify.parse_message(message_type)` to customize message parsers.

```python
@line_dify.parse_message("location")
async def parse_location_message(message):
    text, _ = await line_dify.parse_location_message(message)
    map_image = get_map_image(message.address)
    return (text, map_image)
```


### Format Request

Use `@line_dify.format_request_text` to format request. (e.g. apply the template)

```python
@line_dify.format_request_text
async def format_request_text(request_text, image_bytes):
    return f"""The user's input is as follows. Think before providing a response:

{request_text}
"""
```


### Inputs

Use `@line_dify.make_inputs` to customize `inputs` as arguments for Dify conversation threads.

```python
@line_dify.make_inputs
async def make_inputs(session: ConversationSession):
    # You can use session to customize inputs dynamically here
    inputs = {
        "line_user_id": session.user_id,
        "favorite_food": "apple"
    }
    
    return inputs
```


### Error Message

Use `@line_dify.to_error_message` to customize reply message when error occurs.

```python
@line_dify.to_error_message
async def to_error_message(event: Event, ex: Exception, session: ConversationSession = None):
    # Custom logic here
    text = random.choice(["Error 🥲", "😵 Something wrong...", "🙃"])
    # Return reply messages
    return [TextMessage(text=text)]
```


## 💾 Conversation Session

Conversation sessions are managed by a database. By default, SQLite is used, but you can specify the file path or database type using `session_db_url`. For the syntax, please refer to SQLAlchemy's documentation.

Additionally, you can specify the session validity period with `session_timeout`. The default is 3600 seconds. If this period elapses since the last conversation, a new conversation thread will be created on Dify when the next conversation starts.

```python
line_dify = LineDify(
    line_channel_access_token=YOUR_CHANNEL_ACCESS_TOKEN,
    line_channel_secret=YOUR_CHANNEL_SECRET,
    dify_api_key=DIFY_API_KEY,
    dify_base_url=DIFY_BASE_URL,
    dify_user=DIFY_USER,
    session_db_url="sqlite:///your_sessions.db",    # SQLAlchemy database url
    session_timeout=1800,                           # Timeout in seconds
)
```


## 🐝 Debug

Set `verbose=True` or environment variable `LINEDIFY_VERBOSE=true` to see the request and response, both from/to LINE and from/to Dify.

```python
line_dify = LineDify(
    line_channel_access_token=YOUR_CHANNEL_ACCESS_TOKEN,
    line_channel_secret=YOUR_CHANNEL_SECRET,
    dify_api_key=DIFY_API_KEY,
    dify_base_url=DIFY_BASE_URL,
    dify_user=DIFY_USER,
    verbose=True
)
```


## 📜 Long-Term Memory

Make function to store message histories. Here is the example for [Zep](https://www.getzep.com):

```sh
pip install zep-python
```

```python
import logging
from zep_python.client import AsyncZep
from zep_python.errors import NotFoundError
from zep_python.types import Message

logger = logging.getLogger(__name__)

class ZepIntegrator:
    def __init__(self, *, api_key: str, base_url: str, cache_size: int = 1000, debug: bool = False):
        self.zep_client = AsyncZep(
            api_key=api_key,
            base_url=base_url
        )
        self.cache_size = cache_size
        self.user_ids = []
        self.session_ids = []
        self.debug = debug

    async def add_user(self, user_id: str):
        try:
            user = await self.zep_client.user.get(
                user_id=user_id
            )
            if self.debug:
                logger.info(f"User found: {user}")
        except NotFoundError:
            user = await self.zep_client.user.add(
                user_id=user_id
            )
            if self.debug:
                logger.info(f"User created: {user}")

        self.user_ids.append(user_id)
        while len(self.user_ids) > self.cache_size:
            self.user_ids.pop(0)

    async def add_session(self, user_id: str, session_id: str):
        try:
            session = await self.zep_client.memory.get_session(
                session_id=session_id
            )
            if self.debug:
                logger.info(f"Session found: {session}")
        except NotFoundError:
            session = await self.zep_client.memory.add_session(
                session_id=session_id,
                user_id=user_id,
            )
            if self.debug:
                logger.info(f"Session created: {session}")

        self.session_ids.append(session_id)
        while len(self.session_ids) > self.cache_size:
            self.session_ids.pop(0)

    async def add_messages(self, user_id: str, session_id: str, request_text: str, response_text: str):
        if not user_id or not session_id or (not request_text and not response_text):
            return

        if user_id not in self.user_ids:
            await self.add_user(user_id)

        if session_id not in self.session_ids:
            await self.add_session(user_id, session_id)

        # Add messages
        messages = []
        if request_text:
            messages.append(Message(role_type="user", content=request_text))
        if response_text:
            messages.append(Message(role_type="assistant", content=response_text))

        if messages:
            await self.zep_client.memory.add(session_id=session_id, messages=messages)
```


Call `add_messages` at the end of processing message event.

```python
zep = ZepIntegrator(
    api_key="YOUR_ZEP_API_KEY",
    base_url="ZEP_BASE_URL"
)

@line_dify.on_message_handling_end
async def on_message_handling_end(
    conversation_session: ConversationSession,
    request_text: str,
    response_text: str,
    response_data: any
):
    await zep.add_messages(
        conversation_session.user_id,
        conversation_session.conversation_id,
        request_text,
        response_text
    )
```

Then you can retrieve the facts about the user from wherever you like, including Dify.


## ⚖️ License

linedify is distributed under the Apache v2 license.

(c)uezo, made with big ❤️ in Tokyo.
