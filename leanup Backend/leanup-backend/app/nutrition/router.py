import httpx
from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.db.supabase import supabase
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/nutrition-logs", tags=["nutrition-logs"])

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
    data = {"user_id": user_id, **log.dict()}
    result = supabase.table("nutrition-logs").insert(data).execute()
    return result.data

# Get all nutrition logs
@router.get("/")
def get_nutrition_logs(user=Depends(get_current_user)):
    user_id = user["sub"]
    result = supabase.table("nutrition-logs").select("*").eq("user_id", user_id).order("logged_at", desc=True).execute()
    return result.data

# Get today's calorie summary
@router.get("/summary/today")
def get_today_summary(user=Depends(get_current_user)):
    user_id = user["sub"]
    from datetime import date
    today = date.today().isoformat()
    result = supabase.table("nutrition-logs").select("calories, protein, carbs, fats").eq("user_id", user_id).gte("logged_at", today).execute()
    logs = result.data
    return {
        "total_calories": sum(l["calories"] for l in logs),
        "total_protein": sum(l["protein"] or 0 for l in logs),
        "total_carbs": sum(l["carbs"] or 0 for l in logs),
        "total_fats": sum(l["fats"] or 0 for l in logs),
    }

# Delete a nutrition log
@router.delete("/{log_id}")
def delete_nutrition_log(log_id: str, user=Depends(get_current_user)):
    user_id = user["sub"]
    supabase.table("nutrition-logs").delete().eq("id", log_id).eq("user_id", user_id).execute()
    return {"message": "Deleted successfully"}

# Search food from Open Food Facts
@router.get("/search")
async def search_food(query: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://world.openfoodfacts.org/cgi/search.pl",
            params={
                "search_terms": query,
                "action": "process",
                "json": True,
                "page_size": 5,
                "fields": "product_name,nutriments"
            }
        )
    
    data = response.json()
    products = data.get("products", [])
    
    results = []
    for product in products:
        nutriments = product.get("nutriments", {})
        results.append({
            "food_name": product.get("product_name", "Unknown"),
            "calories": nutriments.get("energy-kcal_100g", 0),
            "protein": nutriments.get("proteins_100g", 0),
            "carbs": nutriments.get("carbohydrates_100g", 0),
            "fats": nutriments.get("fat_100g", 0),
        })
    
    return {"results": results}