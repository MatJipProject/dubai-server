from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pathlib import Path
import uvicorn

from app.restaurants.router import restaurants_controller
from app.users.router import auth_controller
from app.reviews.router import reviews_controller


BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="맛집 API 서버", version="0.0.1")

app.include_router(
    restaurants_controller.router, prefix="/api/v1/restaurants", tags=["restaurants"]
)
app.include_router(auth_controller.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(
    reviews_controller.router, prefix="/api/v1/reviews", tags=["reviews"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def health_check():
    return JSONResponse({"status": "ok"})
