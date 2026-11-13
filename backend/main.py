import os
import time
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

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
# মূল মডেল ব্যর্থ হলে এই মডেলগুলো ক্রমানুসারে চেষ্টা হবে (কমা দিয়ে আলাদা করুন)
GEMINI_FALLBACK_MODELS = [
    m.strip()
    for m in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-flash-latest").split(",")
    if m.strip()
]
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

RETRIES_PER_MODEL = int(os.getenv("RETRIES_PER_MODEL", "3"))
RETRY_CODES = {429, 500, 502, 503, 504}  # সাময়িক সমস্যা: আবার চেষ্টা করা হবে
SWITCH_CODES = {404}  # মডেল নেই: সরাসরি পরের মডেলে যাওয়া হবে

FRIENDLY_ERROR = (
    "দুঃখিত, এই মুহূর্তে AI সার্ভারে অনেক চাপ। "
    "কিছুক্ষণ পরে আবার মেসেজ পাঠান।"
)

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


class AllModelsFailed(Exception):
    pass


def _error_code(e: Exception):
    code = getattr(e, "code", None)
    return code if isinstance(code, int) else None


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

    models = [GEMINI_MODEL] + [m for m in GEMINI_FALLBACK_MODELS if m != GEMINI_MODEL]
    last_error = None

    for model in models:
        for attempt in range(RETRIES_PER_MODEL):
            started = False
            try:
                for chunk in client.models.generate_content_stream(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                ):
                    if chunk.text:
                        started = True
                        yield chunk.text
                return  # সফল
            except Exception as e:
                if started:
                    raise  # উত্তর অর্ধেক চলে গেছে, আবার শুরু করলে লেখা দ্বিগুণ হবে
                last_error = e
                code = _error_code(e)
                if code in RETRY_CODES:
                    time.sleep(1.5 * (attempt + 1))  # একটু অপেক্ষা করে আবার
                    continue
                if code in SWITCH_CODES:
                    break  # পরের মডেলে যাও
                raise  # key ভুল, অনুরোধ ভুল ইত্যাদি: আবার চেষ্টা করে লাভ নেই

    raise AllModelsFailed(str(last_error))


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
        except AllModelsFailed as e:
            print("All models failed:", e)  # Render-এর Logs-এ আসল কারণ দেখা যাবে
            yield FRIENDLY_ERROR
        except Exception as e:
            print("Error:", e)
            yield f"\n[Error: {e}]"

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")
