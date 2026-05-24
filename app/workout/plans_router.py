from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import get_current_user
from app.db.supabase import supabase
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/workout_plans", tags=["workout_plans"])

class WorkoutPlanExercise(BaseModel):
    exercise_name: str
    exercise_id: Optional[str] = None
    body_part: Optional[str] = None
    target_muscle: Optional[str] = None
    gif_url: Optional[str] = None
    sets: int = 3
    reps: int = 10
    rest_seconds: int = 60
    order_index: int

class CreateWorkoutPlan(BaseModel):
    name: str
    goal: Optional[str] = None
    exercises: list[WorkoutPlanExercise]

PRESET_PLANS = {
    ("beginner", "general_fitness"): {
        "name": "Full Body Starter",
        "exercises": [
            {"exercise_name": "Bodyweight Squat", "sets": 3, "reps": 12, "rest_seconds": 60, "order_index": 0},
            {"exercise_name": "Push Up", "sets": 3, "reps": 10, "rest_seconds": 60, "order_index": 1},
            {"exercise_name": "Dumbbell Row", "sets": 3, "reps": 10, "rest_seconds": 60, "order_index": 2},
            {"exercise_name": "Plank", "sets": 3, "reps": 30, "rest_seconds": 45, "order_index": 3},
        ]
    },
    ("beginner", "lose_weight"): {
        "name": "Fat Burn Basics",
        "exercises": [
            {"exercise_name": "Jumping Jacks", "sets": 3, "reps": 20, "rest_seconds": 30, "order_index": 0},
            {"exercise_name": "Bodyweight Squat", "sets": 3, "reps": 15, "rest_seconds": 30, "order_index": 1},
            {"exercise_name": "Mountain Climbers", "sets": 3, "reps": 20, "rest_seconds": 30, "order_index": 2},
            {"exercise_name": "Push Up", "sets": 3, "reps": 10, "rest_seconds": 30, "order_index": 3},
            {"exercise_name": "Burpee", "sets": 3, "reps": 8, "rest_seconds": 45, "order_index": 4},
        ]
    },
    ("beginner", "build_muscle"): {
        "name": "Beginner Strength",
        "exercises": [
            {"exercise_name": "Barbell Squat", "sets": 3, "reps": 8, "rest_seconds": 90, "order_index": 0},
            {"exercise_name": "Bench Press", "sets": 3, "reps": 8, "rest_seconds": 90, "order_index": 1},
            {"exercise_name": "Barbell Row", "sets": 3, "reps": 8, "rest_seconds": 90, "order_index": 2},
            {"exercise_name": "Overhead Press", "sets": 3, "reps": 8, "rest_seconds": 90, "order_index": 3},
            {"exercise_name": "Deadlift", "sets": 3, "reps": 5, "rest_seconds": 120, "order_index": 4},
        ]
    },
    ("intermediate", "build_muscle"): {
        "name": "PPL Program",
        "exercises": [
            {"exercise_name": "Bench Press", "sets": 4, "reps": 8, "rest_seconds": 90, "order_index": 0},
            {"exercise_name": "Incline Dumbbell Press", "sets": 3, "reps": 10, "rest_seconds": 90, "order_index": 1},
            {"exercise_name": "Cable Fly", "sets": 3, "reps": 12, "rest_seconds": 60, "order_index": 2},
            {"exercise_name": "Tricep Pushdown", "sets": 3, "reps": 12, "rest_seconds": 60, "order_index": 3},
            {"exercise_name": "Lateral Raise", "sets": 3, "reps": 15, "rest_seconds": 60, "order_index": 4},
        ]
    },
    ("advanced", "build_muscle"): {
        "name": "Upper/Lower Split",
        "exercises": [
            {"exercise_name": "Barbell Squat", "sets": 5, "reps": 5, "rest_seconds": 120, "order_index": 0},
            {"exercise_name": "Romanian Deadlift", "sets": 4, "reps": 8, "rest_seconds": 90, "order_index": 1},
            {"exercise_name": "Leg Press", "sets": 3, "reps": 12, "rest_seconds": 90, "order_index": 2},
            {"exercise_name": "Leg Curl", "sets": 3, "reps": 12, "rest_seconds": 60, "order_index": 3},
            {"exercise_name": "Calf Raise", "sets": 4, "reps": 15, "rest_seconds": 60, "order_index": 4},
        ]
    },
}

@router.get("/presets")
def get_presets(user=Depends(get_current_user)):
    user_id = user["sub"]
    result = supabase.table("users").select("fitness_level, goal").eq("id", user_id).single().execute()
    profile = result.data
    key = (profile["fitness_level"], profile["goal"])
    preset = PRESET_PLANS.get(key)
    if not preset:
        # fallback to beginner general fitness
        preset = PRESET_PLANS[("beginner", "general_fitness")]
    return preset

@router.get("/")
def get_plans(user=Depends(get_current_user)):
    user_id = user["sub"]
    result = supabase.table("workout_plans").select(
        "*, workout_plan_exercises(*)"
    ).eq("user_id", user_id).order("created_at", desc=True).execute()
    return result.data

@router.post("/")
def create_plan(plan: CreateWorkoutPlan, user=Depends(get_current_user)):
    user_id = user["sub"]

    # check plan limit
    existing = supabase.table("workout_plans").select("id").eq("user_id", user_id).execute()
    if len(existing.data) >= 5:
        raise HTTPException(status_code=400, detail="Maximum 5 plans allowed")

    # create plan
    plan_result = supabase.table("workout_plans").insert({
        "user_id": user_id,
        "name": plan.name,
        "goal": plan.goal,
    }).execute()
    plan_id = plan_result.data[0]["id"]

    # insert exercises
    exercises = [
        {**ex.model_dump(), "plan_id": plan_id}
        for ex in plan.exercises
    ]
    supabase.table("workout_plan_exercises").insert(exercises).execute()

    # return full plan
    result = supabase.table("workout_plans").select(
        "*, workout_plan_exercises(*)"
    ).eq("id", plan_id).single().execute()
    return result.data

@router.delete("/{plan_id}")
def delete_plan(plan_id: str, user=Depends(get_current_user)):
    user_id = user["sub"]
    supabase.table("workout_plans").delete().eq("id", plan_id).eq("user_id", user_id).execute()
    return {"message": "Plan deleted"}

@router.put("/{plan_id}/activate")
def activate_plan(plan_id: str, user=Depends(get_current_user)):
    user_id = user["sub"]
    # deactivate all plans first
    supabase.table("workout_plans").update({"is_active": False}).eq("user_id", user_id).execute()
    # activate selected plan
    result = supabase.table("workout_plans").update({"is_active": True}).eq("id", plan_id).eq("user_id", user_id).execute()
    return result.data