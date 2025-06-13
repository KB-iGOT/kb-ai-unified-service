import json
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.logger import setup_logging
from app.api.routes import role_mapping

def initialize_app() -> FastAPI:
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

    # Setup logging
    setup_logging()
    logger = logging.getLogger("uvicorn.error")

    # Basic request/response logging middleware
    @app.middleware("http")
    async def log_requests(request, call_next):
        logger.info(f"Request: {request.method} {request.url}")
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response

    # Load competency framework at startup
    @app.on_event("startup")
    async def startup_event():
        try:
            framework_path = Path("competency_framework.json")
            with open(framework_path, "r", encoding="utf-8") as f:
                framework = json.load(f)
            role_mapping.set_competency_framework(framework)
        except Exception as e:
            logger.error(f"Failed to load competency framework: {e}")

    # Include routers
    app.include_router(role_mapping.router, prefix="/api/v1")

    return app
