import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import create_client, Client
from app.db.session import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import AuthResponse, UserResponse, UserUpdateRequest
from app.api.deps import get_current_user
from app.db.models.user import User
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

supabase: Client = create_client(settings.supabase_url, settings.supabase_key)


@router.post("/register", response_model=AuthResponse)
async def register(body: dict, db: AsyncSession = Depends(get_db)):
    try:
        auth_response = supabase.auth.sign_up({
            "email": body["email"],
            "password": body["password"],
        })
        supa_user = auth_response.user
        if not supa_user:
            raise HTTPException(status_code=400, detail="Registration failed")

        auth_service = AuthService(db)
        user, token = await auth_service.authenticate_or_create(
            supabase_uid=supa_user.id,
            email=body["email"],
            full_name=body.get("full_name", body["email"].split("@")[0]),
        )
        return AuthResponse(
            access_token=token,
            user=UserResponse.model_validate(user),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Registration error: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=AuthResponse)
async def login(body: dict, db: AsyncSession = Depends(get_db)):
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": body["email"],
            "password": body["password"],
        })
        supa_user = auth_response.user
        if not supa_user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        meta = supa_user.user_metadata or {}
        auth_service = AuthService(db)
        user, token = await auth_service.authenticate_or_create(
            supabase_uid=supa_user.id,
            email=body["email"],
            full_name=meta.get("full_name", meta.get("name", body["email"].split("@")[0])),
        )
        return AuthResponse(
            access_token=token,
            user=UserResponse.model_validate(user),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Login error: %s", str(e))
        raise HTTPException(status_code=401, detail="Invalid credentials")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    auth_service = AuthService(db)
    update_data = body.model_dump(exclude_unset=True)
    user = await auth_service.update_user(current_user.id, **update_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)
