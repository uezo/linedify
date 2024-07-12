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

# LINE Bot - Dify Agent Integrator
line_dify = LineDify(
    line_channel_access_token=YOUR_CHANNEL_ACCESS_TOKEN,
    line_channel_secret=YOUR_CHANNEL_SECRET,
    dify_api_key=DIFY_API_KEY,
    dify_base_url=DIFY_BASE_URL,    # e.g. http://localhost/v1
    dify_user=DIFY_USER
)

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

Implement `line_dify.process_response` to customize the response message.

```python
from typing import List
from linebot.models import SendMessage, TextSendMessage, QuickReply, QuickReplyButton, MessageAction

async def process_response(text: str, data: dict) -> List[SendMessage]:
    response_message = TextSendMessage(text=text)

    # Show QuickReply buttons when tool "reservation" was executed on Dify
    if tool := data.get("tool"):
        if tool == "reservation":
            response_message.quick_reply = QuickReply([
                QuickReplyButton(action=MessageAction(label="Checkout", text="Checkout")),
                QuickReplyButton(action=MessageAction(label="Cancel", text="Cancel"))
            ])

    return [response_message]

# Overwrite process_response
line_dify.process_response = process_response
```


## 😢 Customize Error Message

Set `error_response` to respond static error message.

```python
line_dify = LineDify(
    line_channel_access_token=YOUR_CHANNEL_ACCESS_TOKEN,
    line_channel_secret=YOUR_CHANNEL_SECRET,
    dify_api_key=DIFY_API_KEY,
    dify_base_url=DIFY_BASE_URL,
    dify_user=DIFY_USER,
    error_response="😵 Something wrong..."
)
```

Or, implement `line_dify.make_error_response` to make the error message rich and dynamic.

```python
import random
from linebot.models import MessageEvent

async def make_error_response(seevent: MessageEvent, ex: Exception) -> List[SendMessage]:
    # Custom logic here
    text = random.choice(["Error 🥲", "😵 Something wrong...", "🙃"])
    return [TextSendMessage(text=text)]

# Overwrite process_response
line_dify.make_error_response = make_error_response
```


## 💾 Conversation session

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

Set `verbose=True` to see the request and response, both from/to LINE and from/to Dify.

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


## ⚖️ License

linedify is distributed under the Apache v2 license.

(c)uezo, made with big ❤️ in Tokyo.

