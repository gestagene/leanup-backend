from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import get_current_user
from app.db.supabase import supabase
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/workout_sessions", tags=["workout_sessions"])

class StartSession(BaseModel):
    plan_id: Optional[str] = None
    notes: Optional[str] = None

class LogSet(BaseModel):
    exercise_name: str
    set_number: int
    reps_completed: Optional[int] = None
    weight_kg: Optional[float] = None
    is_completed: bool = True

@router.post("/")
def start_session(body: StartSession, user=Depends(get_current_user)):
    user_id = user["sub"]
    result = supabase.table("workout_sessions").insert({
        "user_id": user_id,
        "plan_id": body.plan_id,
        "notes": body.notes,
    }).execute()
    return result.data[0]

@router.get("/")
def get_sessions(user=Depends(get_current_user)):
    user_id = user["sub"]
    result = supabase.table("workout_sessions").select(
        "*, workout_session_sets(*)"
    ).eq("user_id", user_id).order("started_at", desc=True).execute()
    return result.data

@router.put("/{session_id}/finish")
def finish_session(session_id: str, user=Depends(get_current_user)):
    user_id = user["sub"]
    from datetime import datetime, timezone
    result = supabase.table("workout_sessions").update({
        "is_finished": True,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", session_id).eq("user_id", user_id).execute()
    return result.data[0]

@router.post("/{session_id}/sets")
def log_set(session_id: str, body: LogSet, user=Depends(get_current_user)):
    result = supabase.table("workout_session_sets").insert({
        "session_id": session_id,
        **body.model_dump(),
    }).execute()
    return result.data[0]

@router.get("/{session_id}/sets")
def get_sets(session_id: str, user=Depends(get_current_user)):
    result = supabase.table("workout_session_sets").select("*").eq(
        "session_id", session_id
    ).order("logged_at").execute()
    return result.data