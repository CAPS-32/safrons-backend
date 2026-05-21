from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.expert import router as expert_router
from app.api.hara import router as hara_router
from app.api.health import router as health_router
from app.api.saved_regions import router as saved_regions_router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(hara_router)
    app.include_router(saved_regions_router)
    app.include_router(expert_router)
    app.include_router(admin_router)

    return app


app = create_app()
