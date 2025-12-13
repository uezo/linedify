from enum import Enum
import json
from logging import getLogger, NullHandler
from typing import Dict, Tuple
import aiohttp


logger = getLogger(__name__)
logger.addHandler(NullHandler())


class DifyType(Enum):
    Agent = "Agent"
    Chatbot = "Chatbot"
    TextGenerator = "TextGenerator"
    Workflow = "Workflow"


class DifyAgent:
    def __init__(self, *, api_key: str, base_url: str, user: str, type: DifyType = DifyType.Agent, verbose: bool = False) -> None:
        self.verbose = verbose
        self.api_key = api_key
        self.base_url = base_url
        self.default_user = user
        self.type = type
        self.response_processors = {
            DifyType.Agent: self.process_agent_response,
            DifyType.Chatbot: self.process_chatbot_response,
            DifyType.TextGenerator: self.process_textgenerator_response,
            DifyType.Workflow: self.process_workflow_response
        }
        self.conversation_ids = {}

    async def make_payloads(self, *, text: str, image_bytes: bytes = None, inputs: dict = None, user: str = None) -> Dict:
        payloads = {
            "inputs": inputs or {},
            "query": text,
            "response_mode": "streaming" if self.type == DifyType.Agent else "blocking",
            "user": user or self.default_user,
            "auto_generate_name": False,
        }

        if image_bytes:
            uploaded_image_id = await self.upload_image(image_bytes, user=user)
            if uploaded_image_id:
                payloads["files"] = [{
                    "type": "image",
                    "transfer_method": "local_file",
                    "upload_file_id": uploaded_image_id
                }]
                if not payloads["query"]:
                    payloads["query"] = "." # Set dummy to prevent query empty error
        
        return payloads

    async def upload_image(self, image_bytes: str, user: str = None) -> str:
        form_data = aiohttp.FormData()
        form_data.add_field("file",
            image_bytes,
            filename="image.png",
            content_type="image/png")
        form_data.add_field('user', user or self.default_user)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.base_url + "/files/upload",
                headers={"Authorization": f"Bearer {self.api_key}"},
                data=form_data
            ) as response:
                response_json = await response.json()
                if self.verbose:
                    logger.info(f"File upload response: {json.dumps(response_json, ensure_ascii=False)}")
                response.raise_for_status()
                return response_json["id"]

    async def process_agent_response(self, response: aiohttp.ClientResponse) -> Tuple[str, str, Dict]:
        conversation_id = ""
        response_text = ""
        response_data = {}

        async for r in response.content:
            decoded_r = r.decode("utf-8")
            if not decoded_r.startswith("data:"):
                continue
            chunk = json.loads(decoded_r[5:])

            if self.verbose:
                logger.debug(f"Chunk from Dify: {json.dumps(chunk, ensure_ascii=False)}")

            event_type = chunk["event"]

            if event_type == "agent_message" or event_type == "message":
                conversation_id = chunk["conversation_id"]
                response_text += chunk["answer"]

            elif event_type == "agent_thought":
                if tool := chunk.get("tool"):
                    response_data["tool"] = tool
                if tool_input := chunk.get("tool_input"):
                    response_data["tool_input"] = tool_input
    
            elif event_type == "message_end":
                if retriever_resources := chunk.get("metadata", {}).get("retriever_resources"):
                    response_data["retriever_resources"] = retriever_resources

        return conversation_id, response_text, response_data

    async def process_chatbot_response(self, response: aiohttp.ClientResponse) -> Tuple[str, str, Dict]:
        response_json = await response.json()

        if self.verbose:
            logger.info(f"Response from Dify: {json.dumps(response_json, ensure_ascii=False)}")

        conversation_id = response_json["conversation_id"]
        response_text = response_json["answer"]
        return conversation_id, response_text, {}

    async def process_textgenerator_response(self, response: aiohttp.ClientResponse) -> Tuple[str, str, Dict]:
        if self.verbose:
            logger.info(f"Response from Dify: {json.dumps(await response.json(), ensure_ascii=False)}")

        raise Exception("TextGenerator is not supported for now.")

    async def process_workflow_response(self, response: aiohttp.ClientResponse) -> Tuple[str, str, Dict]:
        if self.verbose:
            logger.info(f"Response from Dify: {json.dumps(await response.json(), ensure_ascii=False)}")

        raise Exception("Workflow is not supported for now.")

    async def invoke(self, *, conversation_id: str, text: str = None, image: bytes = None, inputs: dict = None, user: str = None, start_as_new: bool = False) -> Tuple[str, Dict]:
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        payloads = await self.make_payloads(text=text, image_bytes=image, inputs=inputs, user=user)

        if conversation_id and not start_as_new:
            payloads["conversation_id"] = conversation_id

        async with aiohttp.ClientSession() as session:
            if self.verbose:
                logger.info(f"Request to Dify: {json.dumps(payloads, ensure_ascii=False)}")

            async with session.post(
                self.base_url + "/chat-messages",
                headers=headers,
                json=payloads
            ) as response:

                if response.status != 200:
                    logger.error(f"Error response from Dify: {json.dumps(await response.json(), ensure_ascii=False)}")
                response.raise_for_status()

                response_processor = self.response_processors[self.type]
                conversation_id, response_text, response_data = await response_processor(response)

                return conversation_id, response_text, response_data
