from fastapi import APIRouter
from app.schemas.requests import ProfanityCheckRequest
from app.schemas.responses import ProfanityCheckResponse
from app.services.profanity_service import check_profanity_fasttext, check_profanity_llm
import logging

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

@router.post(
    "/fasttext",
    response_model=ProfanityCheckResponse,
    summary="Check profanity using fastText model"
)
def profanity_check_fasttext(payload: ProfanityCheckRequest):
    logger.info(f"API: Received fastText profanity check for: {payload.text}")
    result = check_profanity_fasttext(payload.text)
    return result  # Return dict directly

@router.post(
    "/llm",
    response_model=ProfanityCheckResponse,
    summary="Check profanity using LLM"
)
def profanity_check_llm(payload: ProfanityCheckRequest):
    logger.info(f"API: Received LLM profanity check for: {payload.text}")
    result = check_profanity_llm(payload.text)
    return result  # Return dict directly
