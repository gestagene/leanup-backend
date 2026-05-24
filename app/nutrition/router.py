import httpx
from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import get_current_user
from app.db.supabase import supabase
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/nutrition_logs", tags=["nutrition_logs"])

class NutritionLog(BaseModel):
    food_name: str
    calories: float
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fats: Optional[float] = None
    meal_type: Optional[str] = None

# Log a meal
@router.post("/")
def log_nutrition(log: NutritionLog, user=Depends(get_current_user)):
    user_id = user["sub"]
    data = {"user_id": user_id, **log.model_dump()}
    result = supabase.table("nutrition_logs").insert(data).execute()
    return result.data

# Get all nutrition logs
@router.get("/")
def get_nutrition_logs(user=Depends(get_current_user)):
    user_id = user["sub"]
    result = supabase.table("nutrition_logs").select("*").eq("user_id", user_id).order("logged_at", desc=True).execute()
    return result.data

# Get today's calorie summary
@router.get("/summary/today")
def get_today_summary(user=Depends(get_current_user)):
    user_id = user["sub"]
    from datetime import date
    today = date.today().isoformat()
    result = supabase.table("nutrition_logs").select("calories, protein, carbs, fats").eq("user_id", user_id).gte("logged_at", today).execute()
    logs = result.data
    return {
        "total_calories": sum(l["calories"] for l in logs),
        "total_protein": sum(l["protein"] or 0 for l in logs),
        "total_carbs": sum(l["carbs"] or 0 for l in logs),
        "total_fats": sum(l["fats"] or 0 for l in logs),
    }

@router.get("/search")
async def search_food(query: str):
    from app.core.config import USDA_API_KEY
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.nal.usda.gov/fdc/v1/foods/search",
                params={
                    "query": query,
                    "api_key": USDA_API_KEY,
                    "pageSize": 8,
                    "dataType": "SR Legacy,Foundation,Survey (FNDDS)",
                }
            )
            response.raise_for_status()

        data = response.json()
        foods = data.get("foods", [])

        results = []
        for food in foods:
            nutrients = {n["nutrientName"]: n["value"] for n in food.get("foodNutrients", [])}
            results.append({
                "food_name": food.get("description", "Unknown"),
                "calories": nutrients.get("Energy", 0),
                "protein": nutrients.get("Protein", 0),
                "carbs": nutrients.get("Carbohydrate, by difference", 0),
                "fats": nutrients.get("Total lipid (fat)", 0),
            })

        return {"results": results}

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Food search timed out, please try again")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"USDA API error: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    
# Delete a nutrition log
@router.delete("/{log_id}")
def delete_nutrition_log(log_id: str, user=Depends(get_current_user)):
    user_id = user["sub"]
    supabase.table("nutrition_logs").delete().eq("id", log_id).eq("user_id", user_id).execute()
    return {"message": "Deleted successfully"}

# Search food from USDA
