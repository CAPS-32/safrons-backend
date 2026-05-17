from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
    }


@router.get(f"{settings.api_v1_prefix}/health")
def versioned_health_check() -> dict[str, str]:
    return health_check()

