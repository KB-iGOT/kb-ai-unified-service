import json
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.logger import setup_logging
from app.api.routes import role_mapping, profanity
from app.services.redis_service import RedisService
from app.core.config import initialize_app

def create_app() -> FastAPI:
    app = FastAPI(
        title="kb-ai-unified-service",
        description="Unified Service for KB AI services requirements",
        version="1.0.0"
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app

app = create_app()
logger = setup_logging()

# Load the competency framework
try:
    with open("competency_framework.json", "r") as f:
        competency_framework = json.load(f)
    role_mapping.set_competency_framework(competency_framework)
except Exception as e:
    logger.error(f"Error loading competency framework: {e}")
    competency_framework = None

# Include the role_mapping and profanity routers
app.include_router(role_mapping.router, prefix="/api/v1")
app.include_router(profanity.router, prefix="/api/v1/profanity")

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker healthcheck"""
    try:
        # Check Redis connection
        redis_service = RedisService()
        redis_service.redis_client.ping()
        
        return {
            "status": "healthy",
            "redis": "connected",
            "competency_framework": "loaded" if competency_framework else "not_loaded"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
