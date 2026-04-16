"""Auth router — login and current-user info."""
import uuid
from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..config import get_settings
from ..models.models import RFAUser, RFAOrganization, RFAAuditLog
from ..middleware.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ─────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str
    role: str
    org_id: str
    org_name: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    org_id: str
    org_name: str
    is_active: bool
    created_at: str | None = None
    last_login: str | None = None


# ── Helpers ─────────────────────────────────────────────────────────────────
def _create_access_token(user_id: str, email: str, role: str, org_id: str) -> str:
    settings = get_settings()
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "org_id": org_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# ── Endpoints ───────────────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with email and password, return a JWT."""
    result = await db.execute(
        select(RFAUser).where(RFAUser.email == body.email.lower().strip())
    )
    user = result.scalar_one_or_none()

    if not user or not bcrypt.checkpw(body.password.encode(), user.password_hash.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Fetch org
    org_result = await db.execute(
        select(RFAOrganization).where(RFAOrganization.id == user.org_id)
    )
    org = org_result.scalar_one_or_none()
    if not org or not org.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is deactivated",
        )

    # Update last_login
    user.last_login = datetime.now(timezone.utc)

    # Audit log
    audit = RFAAuditLog(
        id=uuid.uuid4(),
        org_id=user.org_id,
        user_id=user.id,
        user_email=user.email,
        action="login",
        resource_type="user",
        resource_id=user.id,
        description=f"User {user.email} logged in",
    )
    db.add(audit)
    await db.flush()

    token = _create_access_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role,
        org_id=str(user.org_id),
    )

    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        org_id=str(user.org_id),
        org_name=org.name,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the currently authenticated user's profile."""
    # Fetch org name
    org_result = await db.execute(
        select(RFAOrganization).where(RFAOrganization.id == current_user.org_id)
    )
    org = org_result.scalar_one_or_none()

    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        org_id=str(current_user.org_id),
        org_name=org.name if org else "",
        is_active=current_user.is_active,
        created_at=str(current_user.created_at) if current_user.created_at else None,
        last_login=str(current_user.last_login) if current_user.last_login else None,
    )
