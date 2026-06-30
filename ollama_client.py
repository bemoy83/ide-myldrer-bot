import json
import httpx
from prompt import RETRY_MESSAGE

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "gemma4"
TIMEOUT = 180.0


async def chat(messages: list[dict]) -> dict:
    """Call Ollama and return parsed JSON. Retries once with correction if parsing fails (FR3)."""
    raw = await _call_ollama(messages)
    parsed = _parse(raw)
    if parsed is not None:
        return parsed

    retry_messages = messages + [
        {"role": "assistant", "content": raw},
        {"role": "user", "content": RETRY_MESSAGE},
    ]
    raw2 = await _call_ollama(retry_messages)
    parsed2 = _parse(raw2)
    if parsed2 is not None:
        return parsed2

    return {"type": "error", "raw": raw2}


async def _call_ollama(messages: list[dict]) -> str:
    payload = {
        "model": MODEL,
        "messages": messages,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.7},
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(OLLAMA_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
    return data["message"]["content"]


async def freeform_chat(messages: list[dict]) -> dict:
    """Call Ollama without JSON format constraint — for post-summary free dialogue."""
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.7},
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(OLLAMA_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
    return {"type": "freeform", "text": data["message"]["content"]}


def _parse(raw: str) -> dict | None:
    try:
        obj = json.loads(raw)
        if obj.get("type") in ("question", "summary"):
            return obj
    except (json.JSONDecodeError, AttributeError):
        pass
    return None
