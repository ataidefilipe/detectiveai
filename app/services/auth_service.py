import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.infra.db import SessionLocal
from app.infra.db_models import UserModel

security = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Gera um token JWT para a sessão da aplicação."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodifica e valida a assinatura/expiração do token JWT."""
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except (jwt.PyJWTError, Exception):
        return None


def verify_google_id_token(token: str, is_mock: bool = False, mock_email: Optional[str] = None, mock_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Valida o Google ID Token fornecido pelo Google Identity Services (frontend).
    Caso o Google Client ID não esteja configurado no .env ou is_mock seja solicitado,
    retorna um perfil mock de teste.
    """
    # Modo Mock / Dev
    if is_mock or not settings.GOOGLE_CLIENT_ID or token.startswith("mock-"):
        email = mock_email or "detetive@detective.ai"
        name = mock_name or "Detetive Convidado"
        return {
            "google_sub": f"mock-sub-{email}",
            "email": email,
            "name": name,
            "picture": "https://api.dicebear.com/7.x/bottts/svg?seed=detective",
        }

    # Validação Oficial Google
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )

        email = idinfo.get("email")
        if not email:
            raise ValueError("O token do Google não contém e-mail.")

        return {
            "google_sub": idinfo.get("sub"),
            "email": email,
            "name": idinfo.get("name", "Detetive"),
            "picture": idinfo.get("picture"),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token Google inválido: {str(exc)}"
        )


def get_or_create_user(user_data: Dict[str, Any], db: Session) -> UserModel:
    """Recupera ou cadastra um usuário pelo email / google_sub."""
    user = None
    if user_data.get("google_sub"):
        user = db.query(UserModel).filter(UserModel.google_sub == user_data["google_sub"]).first()

    if not user and user_data.get("email"):
        user = db.query(UserModel).filter(UserModel.email == user_data["email"]).first()

    if not user:
        user = UserModel(
            google_sub=user_data.get("google_sub"),
            email=user_data["email"],
            name=user_data.get("name", "Detetive"),
            picture=user_data.get("picture"),
            is_active=True,
            role="player"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Atualiza nome/foto se mudou
        updated = False
        if user_data.get("name") and user.name != user_data["name"]:
            user.name = user_data["name"]
            updated = True
        if user_data.get("picture") and user.picture != user_data["picture"]:
            user.picture = user_data["picture"]
            updated = True
        if user_data.get("google_sub") and not user.google_sub:
            user.google_sub = user_data["google_sub"]
            updated = True
        if updated:
            db.commit()
            db.refresh(user)

    return user


def get_current_user_optional(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[UserModel]:
    """Retorna o UserModel atual se o token Bearer for válido, senão None (não bloqueia)."""
    if not auth or not auth.credentials:
        return None

    payload = decode_access_token(auth.credentials)
    if not payload or "sub" not in payload:
        return None

    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        return None

    user = db.query(UserModel).filter(UserModel.id == user_id, UserModel.is_active == True).first()
    return user


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> UserModel:
    """Exige que a requisição contenha um token Bearer válido de usuário ativo."""
    user = get_current_user_optional(auth, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user
