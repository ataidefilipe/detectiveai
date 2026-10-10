from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.auth_service import (
    get_db,
    verify_google_id_token,
    get_or_create_user,
    create_access_token,
    get_current_user
)
from app.infra.db_models import UserModel

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleLoginRequest(BaseModel):
    credential: Optional[str] = None
    is_mock: Optional[bool] = False
    mock_email: Optional[str] = None
    mock_name: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    picture: Optional[str] = None
    role: str
    created_at: Optional[str] = None


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AuthConfigResponse(BaseModel):
    google_client_id: Optional[str]
    mock_available: bool = True


@router.get("/config", response_model=AuthConfigResponse)
def get_auth_config():
    """Retorna a configuração de autenticação para o frontend."""
    return AuthConfigResponse(
        google_client_id=settings.GOOGLE_CLIENT_ID if settings.GOOGLE_CLIENT_ID else None,
        mock_available=True
    )


@router.post("/google", response_model=AuthTokenResponse)
def login_with_google(payload: GoogleLoginRequest, db: Session = Depends(get_db)):
    """
    Autentica via Google ID Token (ou mock dev se o Google Client ID não estiver configurado).
    Cria ou recupera o usuário e retorna o JWT de sessão.
    """
    token = payload.credential or ""
    user_info = verify_google_id_token(
        token=token,
        is_mock=bool(payload.is_mock),
        mock_email=payload.mock_email,
        mock_name=payload.mock_name
    )

    user = get_or_create_user(user_info, db)

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})

    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            picture=user.picture,
            role=user.role,
            created_at=user.created_at.isoformat() if user.created_at else None
        )
    )


@router.get("/me", response_model=UserResponse)
def get_authenticated_user_profile(user: UserModel = Depends(get_current_user)):
    """Retorna os dados do usuário autenticado atual."""
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        picture=user.picture,
        role=user.role,
        created_at=user.created_at.isoformat() if user.created_at else None
    )
