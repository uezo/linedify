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

Implement function to edit reply message below the decorator `@line_dify.to_reply_message`.

```python
from typing import List
from linebot.models import SendMessage, TextSendMessage, QuickReply, QuickReplyButton, MessageAction
from linedify.session import ConversationSession

@line_dify.to_reply_message
async def to_reply_message(text: str, data: dict, session: ConversationSession) -> List[SendMessage]:
    response_message = TextSendMessage(text=text)

    # Show QuickReply buttons when tool "reservation" was executed on Dify
    if tool := data.get("tool"):
        if tool == "reservation":
            response_message.quick_reply = QuickReply([
                QuickReplyButton(action=MessageAction(label="Checkout", text="Checkout")),
                QuickReplyButton(action=MessageAction(label="Cancel", text="Cancel"))
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
        # Return the list of SendMessage to reply immediately without processing the event
        return [TextSendMessage("Forbidden")]
```


### Handle events

Use `@line_dify.event(event_type)` to customize event handlers.

```python
# Add handler for Postback event
@line_dify.event("postback")
async def handle_message_event(event: PostbackEvent):
    # Do something here
    # Return reply messages
    return [TextSendMessage(f"Response for postback event: {event.postback.data}")]

# Add handler for unspecified event
@line_dify.event()
async def handle_event(event):
    # Do something here
    # Return reply messages
    return [TextSendMessage(f"Response for event type: {event.type}")]
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
    return [TextSendMessage(text=text)]
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

