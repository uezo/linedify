import pytest
import types
import sys
import asyncio
import importlib.util
from pathlib import Path

# Provide dummy linebot modules so linedify can be imported without dependency.
sys.modules.setdefault("linebot", types.ModuleType("linebot"))
sys.modules.setdefault("linebot.v3", types.ModuleType("linebot.v3"))
sys.modules.setdefault("linebot.v3.messaging", types.ModuleType("linebot.v3.messaging"))
sys.modules.setdefault("linebot.v3.webhooks", types.ModuleType("linebot.v3.webhooks"))

# Provide dummy aiohttp module so importing dify does not fail when aiohttp is not installed.
aiohttp_stub = types.ModuleType("aiohttp")
aiohttp_stub.ClientSession = object
aiohttp_stub.ClientResponse = object
aiohttp_stub.FormData = object
sys.modules.setdefault("aiohttp", aiohttp_stub)

# Import linedify.dify without triggering linedify.__init__
spec = importlib.util.spec_from_file_location(
    "linedify.dify", str(Path(__file__).resolve().parents[1] / "linedify" / "dify.py")
)
dify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dify)
DifyAgent = dify.DifyAgent
DifyType = dify.DifyType

class FakeContent:
    def __init__(self, chunks):
        self.chunks = [c.encode('utf-8') for c in chunks]
    def __aiter__(self):
        return self
    async def __anext__(self):
        if not self.chunks:
            raise StopAsyncIteration
        return self.chunks.pop(0)

class FakeResponse:
    def __init__(self, chunks):
        self.content = FakeContent(chunks)

def build_chunks():
    return [
        'data: {"event": "message", "conversation_id": "cid1", "answer": "Hello"}\n\n',
        'data: {"event": "message_end", "conversation_id": "cid1", "metadata": {}}\n\n'
    ]

def test_process_agent_response_new_spec():
    agent = DifyAgent(api_key="x", base_url="http://example", user="u", type=DifyType.Agent)
    resp = FakeResponse(build_chunks())
    conv_id, text, data = asyncio.get_event_loop().run_until_complete(
        agent.process_agent_response(resp)
    )
    assert conv_id == "cid1"
    assert text == "Hello"
    assert data == {}
