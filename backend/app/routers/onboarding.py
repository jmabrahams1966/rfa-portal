"""Onboarding router — org + admin user creation in one call."""
import uuid
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models.models import RFAOrganization, RFAUser, RFAAuditLog

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# ── Schemas ─────────────────────────────────────────────────────────────────
class SignupRequest(BaseModel):
    org_name: str
    org_type: str  # carrier / tpa / self_insured / law_firm
    admin_email: str
    admin_name: str
    admin_password: str
    w_number: str | None = None


class SignupResponse(BaseModel):
    org_id: str
    org_name: str
    org_type: str
    user_id: str
    email: str
    full_name: str
    role: str
    message: str


VALID_ORG_TYPES = {"carrier", "tpa", "self_insured", "law_firm"}


# ── Endpoints ───────────────────────────────────────────────────────────────
@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    body: SignupRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create an organization and its first admin user in a single call.

    No authentication required — this is the public signup endpoint.
    """
    # Validate org_type
    if body.org_type not in VALID_ORG_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid org_type. Must be one of: {', '.join(sorted(VALID_ORG_TYPES))}",
        )

    # Validate password strength
    if len(body.admin_password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    # Check for existing email
    email = body.admin_email.lower().strip()
    existing = await db.execute(select(RFAUser).where(RFAUser.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create organization
    org = RFAOrganization(
        id=uuid.uuid4(),
        name=body.org_name.strip(),
        org_type=body.org_type,
        w_number=body.w_number,
        plan_tier="starter",
        is_active=True,
        contact_name=body.admin_name.strip(),
        contact_email=email,
    )
    db.add(org)
    await db.flush()

    # Create admin user
    password_hash = bcrypt.hashpw(
        body.admin_password.encode(), bcrypt.gensalt()
    ).decode()

    user = RFAUser(
        id=uuid.uuid4(),
        org_id=org.id,
        email=email,
        password_hash=password_hash,
        full_name=body.admin_name.strip(),
        role="admin",
        is_active=True,
    )
    db.add(user)

    # Audit log
    db.add(RFAAuditLog(
        id=uuid.uuid4(),
        org_id=org.id,
        user_id=user.id,
        user_email=email,
        action="signup",
        resource_type="organization",
        resource_id=org.id,
        description=f"Org '{org.name}' created with admin {email}",
    ))

    await db.flush()

    return SignupResponse(
        org_id=str(org.id),
        org_name=org.name,
        org_type=org.org_type,
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        message="Organization and admin account created successfully",
    )
