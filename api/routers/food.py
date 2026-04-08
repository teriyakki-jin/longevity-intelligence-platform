"""Food recognition endpoint (placeholder — full CV model in Phase 7)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from longevity.common.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class FoodDetection(BaseModel):
    name: str
    confidence: float
    portion_estimate_g: float


class NutritionInfo(BaseModel):
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    sodium_mg: float


class FoodResponse(BaseModel):
    success: bool
    foods_detected: list[FoodDetection]
    total_nutrition: NutritionInfo
    health_score: float
    bioage_impact: str


@router.post("/recognize", response_model=FoodResponse)
async def recognize_food(file: UploadFile = File(...)) -> FoodResponse:
    """Recognize food from photo and return nutritional analysis."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Placeholder response until CV model is trained
    logger.info("food_recognition_request", filename=file.filename)
    return FoodResponse(
        success=True,
        foods_detected=[
            FoodDetection(name="Mixed meal (CV model pending training)", confidence=0.0, portion_estimate_g=0)
        ],
        total_nutrition=NutritionInfo(
            calories=0, protein_g=0, carbs_g=0, fat_g=0, fiber_g=0, sodium_mg=0
        ),
        health_score=0.0,
        bioage_impact="unknown — train food recognition model first",
    )
