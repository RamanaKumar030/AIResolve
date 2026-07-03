from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.admin import router as admin_router
from app.api.v1.knowledge_base import router as knowledge_base_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
v1_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
v1_router.include_router(feedback_router, prefix="/feedback", tags=["Feedback"])
v1_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
v1_router.include_router(knowledge_base_router, prefix="/knowledge-base", tags=["Knowledge Base"])
