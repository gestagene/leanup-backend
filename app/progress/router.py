from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import get_current_user
from app.db.supabase import supabase
from pydantic import BaseModel
from typing import Optional
from datetime import date, timedelta, datetime, timezone

router = APIRouter(prefix="/progress", tags=["progress"])

class ProgressLog(BaseModel):
    weight: float
    body_fat_percentage: Optional[float] = None
    notes: Optional[str] = None

@router.post("/streak/checkin")
def checkin(user=Depends(get_current_user)):
    user_id = user["sub"]
    today = date.today().isoformat()

    # check if already checked in today
    existing = supabase.table("daily_checkins").select("*").eq(
        "user_id", user_id
    ).eq("date", today).execute()

    if existing.data:
        # already checked in, just return current streak
        streak = supabase.table("daily_checkins").select("*").eq(
            "user_id", user_id
        ).order("date", desc=True).execute().data
        return {"streak": len(streak), "already_checked_in": True}

    # insert today's checkin
    supabase.table("daily_checkins").insert({
        "user_id": user_id,
        "date": today,
    }).execute()

    # calculate streak — count consecutive days going back from today
    checkins = supabase.table("daily_checkins").select("date").eq(
        "user_id", user_id
    ).order("date", desc=True).execute().data

    streak = 0
    expected = date.today()
    for checkin in checkins:
        checkin_date = date.fromisoformat(checkin["date"])
        if checkin_date == expected:
            streak += 1
            expected -= timedelta(days=1)
        else:
            break

    return {"streak": streak, "already_checked_in": False}

@router.get("/streak")
def get_streak(user=Depends(get_current_user)):
    user_id = user["sub"]

    checkins = supabase.table("daily_checkins").select("date").eq(
        "user_id", user_id
    ).order("date", desc=True).execute().data

    if not checkins:
        return {"streak": 0}

    streak = 0
    expected = date.today()
    for checkin in checkins:
        checkin_date = date.fromisoformat(checkin["date"])
        if checkin_date == expected:
            streak += 1
            expected -= timedelta(days=1)
        else:
            break

    return {"streak": streak}

@router.post("/")
def log_progress(log: ProgressLog, user=Depends(get_current_user)):
    user_id = user["sub"]
    data = {"user_id": user_id, **log.model_dump()}
    result = supabase.table("progress_logs").insert(data).execute()
    return result.data

@router.get("/")
def get_progress(user=Depends(get_current_user)):
    user_id = user["sub"]
    result = supabase.table("progress_logs").select("*").eq("user_id", user_id).order("logged_at", desc=True).execute()
    return result.data

@router.get("/analytics")
def get_analytics(user=Depends(get_current_user)):
    user_id = user["sub"]

    progress = supabase.table("progress_logs").select("*").eq("user_id", user_id).order("logged_at").execute().data
    workouts = supabase.table("workout_sessions").select("*").eq("user_id", user_id).eq("is_finished", True).execute().data
    nutrition = supabase.table("nutrition_logs").select("calories").eq("user_id", user_id).execute().data
    workout_logs = supabase.table("workout_logs").select("*").eq("user_id", user_id).execute().data

    # weight chart data — ordered oldest to newest for charting
    weight_history = [
        {"date": p["logged_at"], "weight": p["weight"]}
        for p in progress
    ]

    # body fat chart data
    body_fat_history = [
        {"date": p["logged_at"], "body_fat": p["body_fat_percentage"]}
        for p in progress
        if p.get("body_fat_percentage") is not None
    ]

    # workout frequency — count per week
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    week_ago = (now - timedelta(days=7)).isoformat()
    month_ago = (now - timedelta(days=30)).isoformat()

    workouts_this_week = len([
        w for w in workouts
        if w["finished_at"] and w["finished_at"] > week_ago
    ])
    workouts_this_month = len([
        w for w in workouts
        if w["finished_at"] and w["finished_at"] > month_ago
    ])

    return {
        # summary cards
        "total_workouts": len(workouts),
        "workouts_this_week": workouts_this_week,
        "workouts_this_month": workouts_this_month,
        "total_calories_logged": round(sum(n["calories"] for n in nutrition), 1),
        "progress_entries": len(progress),

        # weight
        "latest_weight": progress[-1]["weight"] if progress else None,
        "starting_weight": progress[0]["weight"] if progress else None,
        "weight_change": round(progress[-1]["weight"] - progress[0]["weight"], 2) if len(progress) > 1 else None,
        "weight_history": weight_history,

        # body fat
        "latest_body_fat": body_fat_history[-1]["body_fat"] if body_fat_history else None,
        "body_fat_history": body_fat_history,
    }
@router.get("/tdee")
def get_tdee(user=Depends(get_current_user)):
    user_id = user["sub"]

    result = supabase.table("users").select("*").eq("id", user_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    p = result.data

    # BMR
    if p["sex"] == "male":
        bmr = (10 * p["weight"]) + (6.25 * p["height"]) - (5 * p["age"]) + 5
    else:
        bmr = (10 * p["weight"]) + (6.25 * p["height"]) - (5 * p["age"]) - 161

    # Activity multiplier
    multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }
    multiplier = multipliers.get(p.get("fitness_level", "moderate"), 1.55)
    tdee = round(bmr * multiplier)

    # Goal adjustment
    goal_adjustments = {
        "lose_weight": -500,
        "maintain": 0,
        "gain_muscle": 300,
    }
    adjustment = goal_adjustments.get(p.get("goal", "maintain"), 0)
    target_calories = tdee + adjustment

    # Protein target (standard: 2g per kg of bodyweight)
    target_protein = round(p["weight"] * 2)

    return {
        "bmr": round(bmr),
        "tdee": tdee,
        "target_calories": target_calories,
        "target_protein": target_protein,
        "target_carbs": round((target_calories * 0.45) / 4),   # 45% from carbs
        "target_fats": round((target_calories * 0.25) / 9),    # 25% from fat
        "goal": p.get("goal"),
        "adjustment": adjustment,
    }
@router.post("/insight")
async def get_ai_insight(data: dict, user=Depends(get_current_user)):
    from app.core.config import GROQ_API_KEY
    import httpx

    prompt = f"""
    You are a fitness coach. Analyze this user's data and give ONE concise, 
    actionable insight in 1-2 sentences. Be specific, encouraging, and direct.
    Do not use bullet points or headers.

    User data:
    - Goal: {data.get('goal', 'unknown')}
    - Workouts this week: {data.get('workouts_this_week', 0)}
    - Total workouts logged: {data.get('total_workouts', 0)}
    - Average calories per meal: {data.get('avg_calories', 0)} kcal (target: {data.get('target_calories', 0)} kcal/day)
    - Average protein per meal: {data.get('avg_protein', 0)}g (target: {data.get('target_protein', 0)}g/day)
    - Current weight: {data.get('latest_weight', 'unknown')} kg
    - Weight change since start: {data.get('weight_change', 'unknown')} kg
    """

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 128,
                },
            )
            response.raise_for_status()

        reply = response.json()["choices"][0]["message"]["content"]
        return {"insight": reply.strip()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))