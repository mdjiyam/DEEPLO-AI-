import os
from typing import List, Literal

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv()

# PROVIDER=gemini (বিনামূল্যে শুরু করার জন্য) অথবা PROVIDER=claude (পরে টাকা দিলে)
PROVIDER = os.getenv("PROVIDER", "gemini").lower()
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "তুমি একজন সহায়ক AI assistant। ব্যবহারকারী যে ভাষায় লেখে, সেই ভাষায় উত্তর দাও।",
)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

app = FastAPI(title="AI Chat Backend")

# Development-এর জন্য সব origin খোলা। Production-এ নির্দিষ্ট domain দিন।
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]  # পুরো কথোপকথন (history সহ)


def stream_gemini(messages: List[Message]):
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    contents = [
        {
            "role": "user" if m.role == "user" else "model",
            "parts": [{"text": m.content}],
        }
        for m in messages
    ]
    for chunk in client.models.generate_content_stream(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    ):
        if chunk.text:
            yield chunk.text


def stream_claude(messages: List[Message]):
    from anthropic import Anthropic

    client = Anthropic()  # ANTHROPIC_API_KEY env থেকে নেবে
    with client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[m.model_dump() for m in messages],
    ) as stream:
        for text in stream.text_stream:
            yield text


@app.get("/health")
def health():
    return {"status": "ok", "provider": PROVIDER}


@app.post("/chat")
def chat(req: ChatRequest):
    """Reply টুকরো টুকরো করে (streaming) পাঠায়।"""

    def generate():
        try:
            source = stream_claude if PROVIDER == "claude" else stream_gemini
            yield from source(req.messages)
        except Exception as e:  # সহজ error handling
            yield f"\n[Error: {e}]"

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")
