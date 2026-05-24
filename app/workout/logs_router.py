from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.db.supabase import supabase
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/workout_logs", tags=["workout_logs"])

class WorkoutLog(BaseModel):
    exercise_name: str
    sets: Optional[int] = None
    reps: Optional[int] = None
    weight_kg: Optional[float] = None  # add this
    duration_minutes: Optional[int] = None
    calories_burned: Optional[float] = None
    notes: Optional[str] = None

@router.post("/")
def log_workout(log: WorkoutLog, user=Depends(get_current_user)):
    user_id = user["sub"]
    data = {"user_id": user_id, **log.model_dump()}
    result = supabase.table("workout_logs").insert(data).execute()
    return result.data

@router.get("/")
def get_workout_logs(user=Depends(get_current_user)):
    user_id = user["sub"]
    result = supabase.table("workout_logs").select("*").eq("user_id", user_id).order("logged_at", desc=True).execute()
    return result.data

@router.delete("/{log_id}")
def delete_workout_log(log_id: str, user=Depends(get_current_user)):
    user_id = user["sub"]
    supabase.table("workout_logs").delete().eq("id", log_id).eq("user_id", user_id).execute()
    return {"message": "Deleted successfully"}