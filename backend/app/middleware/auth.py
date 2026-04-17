"""JWT authentication middleware with RBAC for RFA-2 Portal.

Supports provider vs non-provider org types with feature-level access control.
"""
import uuid
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models.models import RFAUser, RFAOrganization
from ..config import get_settings
from ..services.rbac_service import has_access, get_user_context

security = HTTPBearer(auto_error=False)


class DevBypassUser:
    """Synthetic super_admin user for development."""
    id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    org_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    email = "dev@rfa-portal.local"
    full_name = "Dev Super Admin"
    role = "super_admin"
    wcb_user_id = None
    is_active = True
    created_at = None
    last_login = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()

    if settings.dev_auth_bypass:
        return DevBypassUser()

    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    result = await db.execute(select(RFAUser).where(RFAUser.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return user


def _get_role(user) -> str:
    role = user.role
    if hasattr(role, "value"):
        return role.value
    return str(role)


# ── Role-Based Guards ────────────────────────────────────────────────────────

def require_role(*roles):
    """Require user to have one of the specified roles."""
    role_strings = [r.value if hasattr(r, "value") else str(r) for r in roles]

    async def checker(current_user=Depends(get_current_user)):
        user_role = _get_role(current_user)
        if user_role not in role_strings and user_role != "super_admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return checker


def require_feature(feature: str):
    """Require user to have access to a specific feature."""
    async def checker(current_user=Depends(get_current_user)):
        user_role = _get_role(current_user)
        if not has_access(user_role, feature):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: your role '{user_role}' does not have access to '{feature}'"
            )
        return current_user
    return checker


# ── Convenience Guards ───────────────────────────────────────────────────────

# Legacy guards (work with any org type)
require_admin = require_role("admin", "practice_admin", "org_admin", "super_admin")
require_adjuster = require_role("admin", "adjuster", "attorney", "practice_admin", "org_admin", "surgeon", "pa_np", "super_admin")
require_reviewer = require_role("admin", "adjuster", "attorney", "reviewer", "paralegal", "practice_admin", "org_admin", "surgeon", "pa_np", "medical_assistant", "billing_staff", "super_admin")
require_any = get_current_user

# Provider-side guards
require_provider = require_role("practice_admin", "surgeon", "pa_np", "super_admin")
require_physician = require_role("practice_admin", "surgeon", "super_admin")
require_provider_staff = require_role("practice_admin", "surgeon", "pa_np", "medical_assistant", "super_admin")

# Non-provider-side guards
require_non_provider = require_role("org_admin", "adjuster", "attorney", "super_admin")
require_filer = require_role("org_admin", "adjuster", "attorney", "super_admin")

# Feature-based guards
require_prior_auth = require_feature("prior_auth.create")
require_prior_auth_submit = require_feature("prior_auth.submit")
require_rfa_filing = require_feature("rfa_1lc.create")
require_compliance = require_feature("compliance.check")
require_batch = require_feature("batch.import")
require_billing = require_feature("billing.manage")

# Super admin
require_super_admin = require_role("super_admin")


# ── User Context Endpoint Helper ─────────────────────────────────────────────

async def get_user_with_context(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get current user with full RBAC context including navigation and features."""
    org = None
    if hasattr(current_user, 'org_id') and current_user.org_id:
        result = await db.execute(select(RFAOrganization).where(RFAOrganization.id == current_user.org_id))
        org = result.scalar_one_or_none()

    return get_user_context(current_user, org)
