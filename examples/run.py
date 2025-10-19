from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, BackgroundTasks
from linedify import LineDify
import os

line_dify = LineDify(
    line_channel_access_token=os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", ""),
    line_channel_secret=os.environ.get("LINE_CHANNEL_SECRET", ""),
    dify_api_key=os.environ.get("DIFY_API_KEY", ""),
    dify_base_url=os.environ.get("DIFY_BASE_URL", ""),
    dify_user=os.environ.get("DIFY_USER", ""),
)

# Room ID to accept messages from
TARGET_ROOM_ID = os.environ.get("TARGET_ROOM_ID")

@line_dify.validate_event
async def validate_event(event):
    if TARGET_ROOM_ID and event.source.type == "room" and event.source.room_id != TARGET_ROOM_ID:
        return []

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

