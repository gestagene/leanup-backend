from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.db.supabase import supabase
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

class UserGoal(str, Enum):
    general_fitness = "general_fitness"
    lose_weight = "lose_weight"
    build_muscle = "build_muscle"
    maintain = "maintain"


class UserFitnessLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class UserSex(str, Enum):
    male = "male"
    female = "female"


class UserProfile(BaseModel):
    name: str
    age: int
    height: float
    weight: float
    sex: Optional[UserSex] = None
    goal: Optional[UserGoal] = None
    fitness_level: Optional[UserFitnessLevel] = None


@router.post("/create-profile")
def create_profile(
    profile: UserProfile,
    user=Depends(get_current_user)
):
    user_id = user["sub"]

    data = {
        "id": user_id,
        **profile.dict()
    }

    result = supabase.table("users").upsert(data).execute()

    return result.data