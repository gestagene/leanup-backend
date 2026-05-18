from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.db.supabase import supabase
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

class UserProfile(BaseModel):
    first_name: str
    age: int
    height: float
    weight: float
    sex: str
    goal: str
    fitness_level: str

@router.post("/create-profile")
def create_profile(profile: UserProfile, user=Depends(get_current_user)):
    user_id = user["sub"]
    data = {"id": user_id, **profile.dict()}
    result = supabase.table("users").upsert(data).execute()
    return result.data