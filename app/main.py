from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.expert import router as expert_router
from app.api.hara import router as hara_router
from app.api.health import router as health_router
from app.api.saved_regions import router as saved_regions_router
from app.api.glossaries import router as glossaries_router
from app.api.expert_glossaries import router as expert_glossaries_router
from app.api.expert_analytics import router as expert_analytics_router
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
    app.include_router(glossaries_router)
    app.include_router(expert_glossaries_router)
    app.include_router(expert_analytics_router)

    @app.on_event("startup")
    def on_startup():
        import sys
        if "pytest" in sys.modules:
            return
        from app.db.session import SessionLocal
        from sqlalchemy import text
        import os
        import glob

        with SessionLocal() as db:
            # Check if migrations have already been run
            try:
                db.execute(text("SELECT 1 FROM hara_bogor LIMIT 1"))
            except Exception:
                db.rollback()
                # Run migrations
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                migrations_dir = os.path.join(base_dir, "database", "migrations")
                sql_files = sorted(glob.glob(os.path.join(migrations_dir, "*.sql")))
                for file_path in sql_files:
                    with open(file_path, "r", encoding="utf-8") as f:
                        sql_content = f.read()
                        db.execute(text(sql_content))
                        db.commit()

        from app.api.saved_regions import ensure_saved_region_tables
        from app.api.expert import ensure_expert_tables
        from app.api.admin import ensure_admin_tables
        from app.api.glossaries import ensure_glossary_tables

        with SessionLocal() as db:
            ensure_saved_region_tables(db)
            ensure_expert_tables(db)
            ensure_admin_tables(db)
            ensure_glossary_tables(db)


    return app



app = create_app()
