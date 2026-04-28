import os
import json
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Multi-Model Chat")
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

AVAILABLE_MODELS = [
    {"id": "claude-opus-4-7", "name": "Claude Opus 4.7", "description": "Most capable, best for complex tasks"},
    {"id": "claude-opus-4-6", "name": "Claude Opus 4.6", "description": "Highly capable, 1M context"},
    {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "description": "Best speed/intelligence balance"},
    {"id": "claude-haiku-4-5", "name": "Claude Haiku 4.5", "description": "Fastest and most cost-effective"},
]


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: list[Message]
    system: str = ""
    use_cache: bool = True


@app.get("/api/models")
def get_models():
    return AVAILABLE_MODELS


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    if not any(m["id"] == req.model for m in AVAILABLE_MODELS):
        raise HTTPException(status_code=400, detail=f"Unknown model: {req.model}")

    async def generate() -> AsyncGenerator[str, None]:
        try:
            messages = [{"role": m.role, "content": m.content} for m in req.messages]

            kwargs = {
                "model": req.model,
                "max_tokens": 8096,
                "messages": messages,
            }

            if req.system:
                if req.use_cache:
                    kwargs["system"] = [
                        {
                            "type": "text",
                            "text": req.system,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ]
                else:
                    kwargs["system"] = req.system

            if req.use_cache and len(messages) > 2:
                last = messages[-1]
                if isinstance(last["content"], str):
                    messages[-1] = {
                        "role": last["role"],
                        "content": [
                            {
                                "type": "text",
                                "text": last["content"],
                                "cache_control": {"type": "ephemeral"},
                            }
                        ],
                    }

            with client.messages.stream(**kwargs) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'type': 'text', 'text': text})}\n\n"

                final = stream.get_final_message()
                usage = {
                    "input_tokens": final.usage.input_tokens,
                    "output_tokens": final.usage.output_tokens,
                    "cache_creation_input_tokens": getattr(final.usage, "cache_creation_input_tokens", 0) or 0,
                    "cache_read_input_tokens": getattr(final.usage, "cache_read_input_tokens", 0) or 0,
                }
                yield f"data: {json.dumps({'type': 'usage', 'usage': usage})}\n\n"
                yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/", response_class=HTMLResponse)
def index():
    with open("index.html") as f:
        return f.read()
