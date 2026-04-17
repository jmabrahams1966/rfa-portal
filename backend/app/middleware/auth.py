"""JWT authentication middleware for RFA-2 Portal."""
import uuid
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models.models import RFAUser
from ..config import get_settings

security = HTTPBearer(auto_error=False)


class DevBypassUser:
    """Synthetic admin user for development."""
    id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    org_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    email = "dev@rfa-portal.local"
    full_name = "Dev Admin"
    role = "admin"
    wcb_user_id = None
    is_active = True
    created_at = None
    last_login = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> RFAUser:
    settings = get_settings()

    # Dev bypass: return a synthetic admin
    if settings.dev_auth_bypass:
        return DevBypassUser()

    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    result = await db.execute(select(RFAUser).where(RFAUser.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return user


def _get_role(user) -> str:
    """Get role as a plain string regardless of enum or varchar."""
    role = user.role
    if hasattr(role, "value"):
        return role.value
    return str(role)


def require_role(*roles):
    role_strings = [r.value if hasattr(r, "value") else str(r) for r in roles]

    async def checker(current_user=Depends(get_current_user)):
        user_role = _get_role(current_user)
        if user_role not in role_strings:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return checker


# Convenience guards
require_admin = require_role("admin")
require_adjuster = require_role("admin", "adjuster")
require_reviewer = require_role("admin", "adjuster", "reviewer")
require_any = get_current_user
