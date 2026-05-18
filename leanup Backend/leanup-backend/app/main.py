from fastapi import FastAPI
from app.auth.router import router as auth_router
from app.users.router import router as users_router
from app.workout.router import router as workout_router
from app.workout.logs_router import router as workout_logs_router
from app.nutrition.router import router as nutrition_router
from app.progress.router import router as progress_router

app = FastAPI(title="Leanup API")

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(workout_router)
app.include_router(workout_logs_router)
app.include_router(nutrition_router)
app.include_router(progress_router)

@app.get("/")
def root():
    return {"message": "Leanup API is running"}