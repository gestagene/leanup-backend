from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import get_current_user
from app.db.supabase import supabase

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me")
def get_my_profile(user=Depends(get_current_user)):
    user_id = user["sub"]
    result = supabase.table("users").select("*").eq("id", user_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    return result.data

@router.put("/me")
def update_my_profile(updates: dict, user=Depends(get_current_user)):
    user_id = user["sub"]
    result = supabase.table("users").update(updates).eq("id", user_id).execute()
    return result.data