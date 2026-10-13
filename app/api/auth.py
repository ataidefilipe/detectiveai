from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.auth_service import (
    get_db,
    verify_google_id_token,
    get_or_create_user,
    create_access_token,
    get_current_user,
    require_admin
)
from app.infra.db_models import UserModel

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleLoginRequest(BaseModel):
    credential: Optional[str] = None
    is_mock: Optional[bool] = False
    mock_email: Optional[str] = None
    mock_name: Optional[str] = None
    is_admin: Optional[bool] = False


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    picture: Optional[str] = None
    role: str
    created_at: Optional[str] = None
    has_custom_openai_key: Optional[bool] = False
    openai_model: Optional[str] = None


def _build_user_response(user: UserModel) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        picture=user.picture,
        role=user.role,
        created_at=user.created_at.isoformat() if user.created_at else None,
        has_custom_openai_key=bool(user.openai_api_key and user.openai_api_key.strip()),
        openai_model=user.openai_model
    )


class UpdateUserRoleRequest(BaseModel):
    role: str


ALLOWED_OPENAI_MODELS: List[str] = ["gpt-6-luna", "gpt-5-mini"]


class AISettingsResponse(BaseModel):
    has_custom_key: bool
    masked_key: Optional[str] = None
    chat_model: Optional[str] = None
    classifier_model: Optional[str] = None
    selected_model: Optional[str] = None
    default_chat_model: str
    default_classifier_model: str
    default_model: str
    available_models: List[str]


class UpdateAISettingsRequest(BaseModel):
    api_key: Optional[str] = None
    chat_model: Optional[str] = None
    classifier_model: Optional[str] = None
    model: Optional[str] = None


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
        mock_name=payload.mock_name,
        is_admin=bool(payload.is_admin)
    )

    user = get_or_create_user(user_info, db)

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})

    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=_build_user_response(user)
    )


@router.get("/me", response_model=UserResponse)
def get_authenticated_user_profile(user: UserModel = Depends(get_current_user)):
    """Retorna os dados do usuário autenticado atual."""
    return _build_user_response(user)


@router.get("/users", response_model=List[UserResponse])
def list_system_users(admin: UserModel = Depends(require_admin), db: Session = Depends(get_db)):
    """[ADMIN] Lista todos os usuários cadastrados no sistema."""
    users = db.query(UserModel).order_by(UserModel.created_at.desc(), UserModel.id.desc()).all()
    return [_build_user_response(u) for u in users]


@router.patch("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    payload: UpdateUserRoleRequest,
    admin: UserModel = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """[ADMIN] Atualiza o papel de um usuário (player ou admin)."""
    if payload.role not in ["player", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role inválida. Deve ser 'player' ou 'admin'."
        )
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")

    user.role = payload.role
    db.commit()
    db.refresh(user)

    return _build_user_response(user)


def _mask_api_key(key: Optional[str]) -> Optional[str]:
    if not key or not key.strip():
        return None
    k = key.strip()
    if len(k) > 8:
        return f"{k[:3]}...{k[-4:]}"
    return "sk-***"


@router.get("/ai-settings", response_model=AISettingsResponse)
def get_user_ai_settings(user: UserModel = Depends(get_current_user)):
    """Retorna as configurações da OpenAI do usuário autenticado."""
    has_key = bool(user.openai_api_key and user.openai_api_key.strip())
    chat_m = user.openai_chat_model or user.openai_model or settings.OPENAI_MODEL
    classifier_m = user.openai_classifier_model or user.openai_model or settings.OPENAI_CLASSIFIER_MODEL
    return AISettingsResponse(
        has_custom_key=has_key,
        masked_key=_mask_api_key(user.openai_api_key),
        chat_model=chat_m,
        classifier_model=classifier_m,
        selected_model=chat_m,
        default_chat_model=settings.OPENAI_MODEL,
        default_classifier_model=settings.OPENAI_CLASSIFIER_MODEL,
        default_model=settings.OPENAI_MODEL,
        available_models=ALLOWED_OPENAI_MODELS
    )


@router.put("/ai-settings", response_model=AISettingsResponse)
def update_user_ai_settings(
    payload: UpdateAISettingsRequest,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Atualiza a chave de API da OpenAI e os modelos de conversa e categorização."""
    if payload.api_key is not None:
        raw_key = payload.api_key.strip()
        if raw_key:
            if not raw_key.startswith("sk-"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Por enquanto apenas chaves da OpenAI são aceitas (devem iniciar com 'sk-')."
                )
            user.openai_api_key = raw_key
        else:
            user.openai_api_key = None

    target_chat = payload.chat_model if payload.chat_model is not None else payload.model
    if target_chat is not None:
        raw_chat = target_chat.strip()
        if raw_chat:
            if raw_chat not in ALLOWED_OPENAI_MODELS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Modelo de conversa inválido. Modelos aceitos no momento: {', '.join(ALLOWED_OPENAI_MODELS)}"
                )
            user.openai_chat_model = raw_chat
            user.openai_model = raw_chat
        else:
            user.openai_chat_model = settings.OPENAI_MODEL
            user.openai_model = settings.OPENAI_MODEL

    if payload.classifier_model is not None:
        raw_classifier = payload.classifier_model.strip()
        if raw_classifier:
            if raw_classifier not in ALLOWED_OPENAI_MODELS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Modelo de categorização inválido. Modelos aceitos no momento: {', '.join(ALLOWED_OPENAI_MODELS)}"
                )
            user.openai_classifier_model = raw_classifier
        else:
            user.openai_classifier_model = settings.OPENAI_CLASSIFIER_MODEL

    db.commit()
    db.refresh(user)

    has_key = bool(user.openai_api_key and user.openai_api_key.strip())
    chat_m = user.openai_chat_model or user.openai_model or settings.OPENAI_MODEL
    classifier_m = user.openai_classifier_model or user.openai_model or settings.OPENAI_CLASSIFIER_MODEL
    return AISettingsResponse(
        has_custom_key=has_key,
        masked_key=_mask_api_key(user.openai_api_key),
        chat_model=chat_m,
        classifier_model=classifier_m,
        selected_model=chat_m,
        default_chat_model=settings.OPENAI_MODEL,
        default_classifier_model=settings.OPENAI_CLASSIFIER_MODEL,
        default_model=settings.OPENAI_MODEL,
        available_models=ALLOWED_OPENAI_MODELS
    )

