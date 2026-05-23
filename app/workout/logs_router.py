from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.db.supabase import supabase
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/workout-logs", tags=["workout-logs"])

class WorkoutLog(BaseModel):
    exercise_name: str
    sets: Optional[int] = None
    reps: Optional[int] = None
    duration_minutes: Optional[int] = None
    calories_burned: Optional[float] = None
    notes: Optional[str] = None

# Log a workout
@router.post("/")
def log_workout(log: WorkoutLog, user=Depends(get_current_user)):
    user_id = user["sub"]
    data = {"user_id": user_id, **log.dict()}
    result = supabase.table("workout-logs").insert(data).execute()
    return result.data

# Get all workout logs
@router.get("/")
def get_workout_logs(user=Depends(get_current_user)):
    user_id = user["sub"]
    result = supabase.table("workout-logs").select("*").eq("user_id", user_id).order("logged_at", desc=True).execute()
    return result.data

# Delete a workout log
@router.delete("/{log_id}")
def delete_workout_log(log_id: str, user=Depends(get_current_user)):
    user_id = user["sub"]
    result = supabase.table("workout-logs").delete().eq("id", log_id).eq("user_id", user_id).execute()
    return {"message": "Deleted successfully"}