import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path

from prompt import SYSTEM_PROMPT, FREEFORM_SYSTEM_PROMPT, FORCE_SUMMARY_MESSAGE
from ollama_client import chat, freeform_chat

app = FastAPI(title="Idé-myldrer Bot")

DEFAULT_MAX_QUESTIONS = 3


class ChatRequest(BaseModel):
    history: list[dict] = []
    user_answer: str
    question_count: int = 0
    phase: str = "questioning"
    max_questions: int = DEFAULT_MAX_QUESTIONS


class ChatResponse(BaseModel):
    response: dict
    history: list[dict]
    question_count: int
    phase: str
    max_questions: int


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    # Build the message list sent to Ollama
    if req.phase == "freeform":
        messages = [{"role": "system", "content": FREEFORM_SYSTEM_PROMPT}]
        messages += req.history
        messages.append({"role": "user", "content": req.user_answer})
        result = await freeform_chat(messages)
    else:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += req.history
        messages.append({"role": "user", "content": req.user_answer})
        if req.question_count >= req.max_questions and req.phase == "questioning":
            messages.append({"role": "user", "content": FORCE_SUMMARY_MESSAGE})
        result = await chat(messages)

    if result.get("type") == "error":
        raise HTTPException(status_code=502, detail=result.get("raw", "Ukjent feil fra modellen"))

    if req.phase == "freeform":
        new_phase = "freeform"
        new_question_count = req.question_count
        assistant_content = result.get("text", "")
    else:
        new_phase = "freeform" if result.get("type") == "summary" else "questioning"
        new_question_count = req.question_count + (1 if result.get("type") == "question" else 0)
        assistant_content = json.dumps(result, ensure_ascii=False)

    updated_history = list(req.history) + [
        {"role": "user", "content": req.user_answer},
        {"role": "assistant", "content": assistant_content},
    ]

    return ChatResponse(
        response=result,
        history=updated_history,
        question_count=new_question_count,
        phase=new_phase,
        max_questions=req.max_questions,
    )


@app.post("/reset")
async def reset():
    return {"ok": True}


# Serve frontend — mount after API routes
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def index():
        return FileResponse(static_dir / "index.html")
