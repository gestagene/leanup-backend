import random
import time

import httpx
from fastapi import APIRouter, Depends, HTTPException

from app.core.config import GROQ_API_KEY
from app.core.dependencies import get_current_user
from app.db.supabase import supabase

router = APIRouter(prefix="/workout", tags=["workout"])

TIMEOUT = 30.0
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

_exercise_cache: list = []
_cache_timestamp: float = 0
CACHE_TTL = 3600  # 1 hour


async def get_all_exercises() -> list:
    global _exercise_cache, _cache_timestamp

    if _exercise_cache and (time.time() - _cache_timestamp) < CACHE_TTL:
        return _exercise_cache

    all_exercises = []
    limit = 200
    offset = 0

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        while True:
            response = await client.get(
                "https://oss.exercisedb.dev/api/v1/exercises",
                params={"limit": limit, "offset": offset},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()
            batch = response.json().get("data", [])
            if not batch:
                break
            all_exercises.extend(batch)
            if len(batch) < limit:
                break
            offset += limit

    _exercise_cache = all_exercises
    _cache_timestamp = time.time()
    return all_exercises


def normalize_exercise(e: dict) -> dict:
    return {
        "id": e.get("exerciseId", ""),
        "name": e.get("name", ""),
        "bodyPart": (e.get("bodyParts") or [""])[0],
        "equipment": (e.get("equipments") or [""])[0],
        "target": (e.get("targetMuscles") or [""])[0],
        "secondaryMuscles": e.get("secondaryMuscles", []),
        "instructions": e.get("instructions", []),
        "gifUrl": e.get("gifUrl", ""),
    }


@router.get("/plan")
async def get_workout_plan(user=Depends(get_current_user)):
    user_id = user["sub"]

    result = supabase.table("users").select("*").eq("id", user_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User profile not found")

    profile = result.data
    prompt = f"""
    Create a 7-day workout plan for this user.

    User stats:
    - Age: {profile['age']}
    - Weight: {profile['weight']}kg
    - Height: {profile['height']}cm
    - Sex: {profile['sex']}
    - Goal: {profile['goal']}
    - Fitness level: {profile['fitness_level']}

    Return ONLY valid JSON in this exact format:
    {{
      "days": [
        {{
          "day": "Monday",
          "focus": "Chest",
          "exercises": [
            {{
              "name": "Push Ups",
              "sets": 3,
              "reps": "12-15"
            }}
          ]
        }}
      ]
    }}

    Do not include markdown.
    Do not include explanations.
    """

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
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 2048,
                },
            )
            response.raise_for_status()

        data = response.json()
        plan = data["choices"][0]["message"]["content"]
        return {"workout_plan": plan}

    except (KeyError, IndexError):
        raise HTTPException(status_code=500, detail="Invalid AI response")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Workout generation timed out")
    except httpx.HTTPStatusError as e:
        print(f"Groq error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=502, detail="AI service error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exercises/search")
async def search_exercises(query: str, user=Depends(get_current_user)):
    exercises = await get_all_exercises()
    filtered = [normalize_exercise(e) for e in exercises if query.lower() in e["name"].lower()]
    return {"results": filtered}


@router.get("/exercises/random")
async def get_random_exercises(user=Depends(get_current_user)):
    exercises = await get_all_exercises()
    return {"results": [normalize_exercise(e) for e in random.sample(exercises, min(10, len(exercises)))]}


@router.get("/exercises/bodyparts")
async def get_bodyparts(user=Depends(get_current_user)):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get("https://oss.exercisedb.dev/api/v1/bodyparts")
            response.raise_for_status()
        return response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exercises/bodypart/{bodypart}")
async def get_exercises_by_bodypart(bodypart: str, user=Depends(get_current_user)):
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"https://oss.exercisedb.dev/api/v1/bodyparts/{bodypart}/exercises",
                params={"limit": 10},
            )
            response.raise_for_status()
        return response.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))