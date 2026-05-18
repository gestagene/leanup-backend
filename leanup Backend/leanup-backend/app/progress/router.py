from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.db.supabase import supabase
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/progress", tags=["progress"])

class ProgressLog(BaseModel):
    weight: float
    body_fat_percentage: Optional[float] = None
    notes: Optional[str] = None

# Log progress
@router.post("/")
def log_progress(log: ProgressLog, user=Depends(get_current_user)):
    user_id = user["sub"]
    data = {"user_id": user_id, **log.dict()}
    result = supabase.table("progress-logs").insert(data).execute()
    return result.data

# Get all progress logs
@router.get("/")
def get_progress(user=Depends(get_current_user)):
    user_id = user["sub"]
    result = supabase.table("progress-logs").select("*").eq("user_id", user_id).order("logged_at", desc=True).execute()
    return result.data

# Analytics dashboard summary
@router.get("/analytics")
def get_analytics(user=Depends(get_current_user)):
    user_id = user["sub"]

    progress = supabase.table("progress-logs").select("*").eq("user_id", user_id).order("logged_at", desc=True).execute().data
    workouts = supabase.table("workout-logs").select("*").eq("user_id", user_id).execute().data
    nutrition = supabase.table("nutrition-logs").select("calories").eq("user_id", user_id).execute().data

    return {
        "total_workouts": len(workouts),
        "total_calories_logged": sum(n["calories"] for n in nutrition),
        "latest_weight": progress[0]["weight"] if progress else None,
        "weight_change": round(progress[-1]["weight"] - progress[0]["weight"], 2) if len(progress) > 1 else None,
        "progress_entries": len(progress),
    }