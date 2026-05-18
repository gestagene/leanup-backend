from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.db.supabase import supabase
from app.core.config import GEMINI_API_KEY
import httpx

router = APIRouter(prefix="/workout", tags=["workout"])

@router.get("/plan")
async def get_workout_plan(user=Depends(get_current_user)):
    user_id = user["sub"]

    result = supabase.table("users").select("*").eq("id", user_id).single().execute()
    profile = result.data

    prompt = f"""
    Create a weekly workout plan for someone with these stats:
    - Age: {profile['age']}
    - Weight: {profile['weight']}kg
    - Height: {profile['height']}cm
    - Sex: {profile['sex']}
    - Goal: {profile['goal']}
    - Fitness level: {profile['fitness_level']}

    Return a structured 7-day workout plan with exercises, sets, and reps.
    """

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]}
        )

    data = response.json()
    plan = data["candidates"][0]["content"]["parts"][0]["text"]
    return {"workout_plan": plan}