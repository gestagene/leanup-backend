import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.config import GROQ_API_KEY
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])

TIMEOUT = 30.0
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are a knowledgeable fitness assistant. "
    "Help users with workout plans, exercise form, nutrition advice, "
    "and general fitness goals. Keep responses concise and practical."
)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


@router.post("/")
async def chat(request: ChatRequest, user=Depends(get_current_user)):
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [{"role": m.role, "content": m.content} for m in request.messages]

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": messages,
                    "max_tokens": 1024,
                },
            )
            response.raise_for_status()

        data = response.json()
        reply = data["choices"][0]["message"]["content"]
        return {"reply": reply}

    except (KeyError, IndexError):
        raise HTTPException(status_code=500, detail="Invalid AI response")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Chat request timed out")
    except httpx.HTTPStatusError as e:
        print(f"Groq error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=502, detail="AI service error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))