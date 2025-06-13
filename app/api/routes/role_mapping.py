from fastapi import APIRouter
import json
import logging
from app.schemas import RoleMappingRequest, RoleMappingResponse, CompetencyItem
from app.services.gemini_llm import map_role_to_competencies_gemini
from app.services.redis_service import RedisService
from fastapi.responses import JSONResponse
from app.prompts import ROLE_MAPPING_PROMPT

logger = logging.getLogger("uvicorn.error")

# This will be set by main.py on startup
competency_framework = None  # Will hold the loaded JSON, not a file path
redis_service = RedisService()  # Initialize Redis service

def set_competency_framework(framework):
    global competency_framework
    competency_framework = framework

router = APIRouter()

def generate_cache_key(organization: str, role_title: str) -> str:
    """Generate a unique cache key for the role mapping request"""
    return f"role_mapping:{organization}:{role_title}"

@router.post(
    "/map_competencies",
    response_model=RoleMappingResponse,
    summary="Map role to competencies using Gemini LLM"
)
def map_role_competencies(payload: RoleMappingRequest):
    if not competency_framework:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Competency framework not loaded"
            }
        )
    prompt_text = ROLE_MAPPING_PROMPT
    try:
        # Generate cache key
        cache_key = generate_cache_key(payload.organization, payload.role_title)
        
        # Try to get from cache first
        cached_result = redis_service.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for role mapping: {cache_key}")
            return RoleMappingResponse(**cached_result)

        # If not in cache, proceed with Gemini LLM call
        logger.info(f"Cache miss for role mapping: {cache_key}")
        competency_framework_json = json.dumps(competency_framework)
        output = map_role_to_competencies_gemini(
            prompt_text=prompt_text,
            competency_framework_json=competency_framework_json,
            organization=payload.organization,
            role_title=payload.role_title,
            department=payload.department
        )
        data = json.loads(output)
        mapped_competencies = []
        for comp in data.get("mapped_competencies", []):
            mapped_competencies.append(CompetencyItem(
                category=comp["category"],
                theme=comp["theme"],
                sub_themes=comp["sub_themes"],
                relevance=str(comp.get("confidence", ""))
            ))
        responsedata = RoleMappingResponse(
            organization=data["organization"],
            role_title=data["role_title"],
            mapped_competencies=mapped_competencies,
            mapping_rationale=data["mapping_rationale"]
        ).dict()

        # Store result in cache before returning
        redis_service.set_with_expiry(cache_key, responsedata)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "status_code": 200,
                "responsedata": responsedata
            }
        )
    except Exception as e:
        logger.error(f"Malformed LLM response: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "status_code": 500,
                "status_msg": "Malformed LLM response",
                "responsedata": None
            }
        )
