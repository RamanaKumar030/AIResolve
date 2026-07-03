import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.v1 import v1_router

settings = get_settings()
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting %s v%s in %s mode",
        settings.app_name,
        settings.app_version,
        settings.environment,
    )
    from sqlalchemy import text as sqltext
    from app.db.session import engine
    async with engine.begin() as conn:
        await conn.execute(sqltext("""
            ALTER TABLE tickets
            ADD COLUMN IF NOT EXISTS recommendation VARCHAR(50),
            ADD COLUMN IF NOT EXISTS recommendation_reasoning TEXT,
            ADD COLUMN IF NOT EXISTS confidence_score DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS conflicts_with_existing_kb BOOLEAN,
            ADD COLUMN IF NOT EXISTS original_answer_was_accurate BOOLEAN,
            ADD COLUMN IF NOT EXISTS original_answer_accuracy_reasoning TEXT;
        """))
        await conn.execute(sqltext("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key VARCHAR(255) PRIMARY KEY,
                value TEXT NOT NULL
            );
        """))
        logger.info("Database schema up-to-date")
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods.split(","),
    allow_headers=settings.cors_allow_headers.split(","),
)

app.include_router(v1_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
