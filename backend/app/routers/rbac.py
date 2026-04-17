"""RBAC Router — user context, org type management, role assignment."""

import uuid
import bcrypt
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from ..database import get_db
from ..models.models import RFAOrganization, RFAUser
from ..middleware.auth import get_current_user, get_user_with_context, require_super_admin, require_admin
from ..services.rbac_service import (
    ORG_TYPES, ROLES, get_roles_for_org_type, validate_role_for_org,
    get_navigation, get_accessible_features, get_org_type_info,
)

router = APIRouter(prefix="/rbac", tags=["rbac"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class CreateOrgRequest(BaseModel):
    name: str
    org_type: str  # provider or non_provider
    subtype: Optional[str] = None  # solo_practice, carrier, law_firm, etc.
    w_number: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None


class CreateUserRequest(BaseModel):
    email: str
    full_name: str
    role: str
    password: Optional[str] = None
    org_id: Optional[str] = None


class UpdateOrgTypeRequest(BaseModel):
    org_id: str
    org_type: str  # provider or non_provider


class UpdateRoleRequest(BaseModel):
    user_id: str
    role: str


# ── User Context ─────────────────────────────────────────────────────────────

@router.get("/context/")
async def get_context(
    context: dict = Depends(get_user_with_context),
):
    """Get current user's full RBAC context — role, org type, navigation, features."""
    return context


@router.get("/org-types/")
async def list_org_types(user=Depends(get_current_user)):
    """List available organization types and their roles."""
    return {
        k: {
            "name": v["name"],
            "description": v["description"],
            "subtypes": v["subtypes"],
            "roles": get_roles_for_org_type(k),
        }
        for k, v in ORG_TYPES.items()
    }


@router.get("/roles/")
async def list_all_roles(user=Depends(get_current_user)):
    """List all available roles."""
    return [{"key": k, **v} for k, v in ROLES.items()]


@router.get("/roles/{org_type}/")
async def list_roles_for_org(org_type: str, user=Depends(get_current_user)):
    """List roles available for a specific org type."""
    return get_roles_for_org_type(org_type)


# ── Super Admin: Organization Management ────────────────────────────────────

@router.get("/organizations/")
async def list_organizations(
    user=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all organizations with their type and user count."""
    orgs = (await db.execute(select(RFAOrganization).order_by(RFAOrganization.created_at.desc()))).scalars().all()
    result = []
    for org in orgs:
        user_count = (await db.execute(
            select(RFAUser).where(RFAUser.org_id == org.id, RFAUser.is_active == True)
        )).scalars().all()
        result.append({
            "id": str(org.id),
            "name": org.name,
            "org_type": org.org_type,
            "is_active": org.is_active,
            "w_number": org.w_number,
            "contact_name": org.contact_name,
            "contact_email": org.contact_email,
            "user_count": len(user_count),
            "created_at": org.created_at.isoformat() if org.created_at else None,
        })
    return {"organizations": result, "total": len(result)}


@router.post("/organizations/")
async def create_organization(
    body: CreateOrgRequest,
    user=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new organization (Super Admin only)."""
    if body.org_type not in ORG_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid org_type. Must be: {list(ORG_TYPES.keys())}")

    org = RFAOrganization(
        id=uuid.uuid4(),
        name=body.name,
        org_type=body.org_type,
        w_number=body.w_number,
        contact_name=body.contact_name,
        contact_email=body.contact_email,
        contact_phone=body.contact_phone,
        is_active=True,
    )
    db.add(org)
    await db.commit()

    return {
        "id": str(org.id),
        "name": org.name,
        "org_type": org.org_type,
        "roles_available": get_roles_for_org_type(body.org_type),
    }


@router.put("/organizations/type/")
async def set_org_type(
    body: UpdateOrgTypeRequest,
    user=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Change an organization's type (Super Admin only). This changes what features are available."""
    if body.org_type not in ORG_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid org_type. Must be: {list(ORG_TYPES.keys())}")

    org = (await db.execute(select(RFAOrganization).where(RFAOrganization.id == uuid.UUID(body.org_id)))).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    old_type = org.org_type
    org.org_type = body.org_type
    await db.commit()

    return {
        "org_id": str(org.id),
        "old_type": old_type,
        "new_type": body.org_type,
        "roles_available": get_roles_for_org_type(body.org_type),
        "message": f"Organization type changed from '{old_type}' to '{body.org_type}'. Users may need role reassignment.",
    }


# ── Super Admin: User Management ────────────────────────────────────────────

@router.get("/users/")
async def list_all_users(
    org_id: Optional[str] = None,
    user=Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users, optionally filtered by org."""
    q = select(RFAUser)
    if org_id:
        q = q.where(RFAUser.org_id == uuid.UUID(org_id))
    users = (await db.execute(q.order_by(RFAUser.created_at.desc()))).scalars().all()

    return {
        "users": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "role_info": ROLES.get(u.role, {}),
                "org_id": str(u.org_id),
                "is_active": u.is_active,
                "last_login": u.last_login.isoformat() if u.last_login else None,
            }
            for u in users
        ],
        "total": len(users),
    }


@router.post("/users/")
async def create_user(
    body: CreateUserRequest,
    user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a user in an organization."""
    # Determine org
    org_id = uuid.UUID(body.org_id) if body.org_id else getattr(user, 'org_id', None)
    if not org_id:
        raise HTTPException(status_code=400, detail="org_id required")

    # Validate role for org type
    org = (await db.execute(select(RFAOrganization).where(RFAOrganization.id == org_id))).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if not validate_role_for_org(body.role, org.org_type):
        valid_roles = [r["key"] for r in get_roles_for_org_type(org.org_type)]
        raise HTTPException(status_code=400, detail=f"Role '{body.role}' is not valid for org type '{org.org_type}'. Valid roles: {valid_roles}")

    # Check email uniqueness
    existing = (await db.execute(select(RFAUser).where(RFAUser.email == body.email.lower()))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    pw_hash = None
    if body.password:
        pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()

    new_user = RFAUser(
        id=uuid.uuid4(),
        org_id=org_id,
        email=body.email.lower(),
        full_name=body.full_name,
        role=body.role,
        password_hash=pw_hash,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()

    return {
        "id": str(new_user.id),
        "email": new_user.email,
        "role": new_user.role,
        "org_id": str(org_id),
        "org_type": org.org_type,
    }


@router.put("/users/role/")
async def update_user_role(
    body: UpdateRoleRequest,
    user=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Change a user's role. Validates against their org type."""
    target = (await db.execute(select(RFAUser).where(RFAUser.id == uuid.UUID(body.user_id)))).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    org = (await db.execute(select(RFAOrganization).where(RFAOrganization.id == target.org_id))).scalar_one_or_none()
    if org and not validate_role_for_org(body.role, org.org_type):
        valid_roles = [r["key"] for r in get_roles_for_org_type(org.org_type)]
        raise HTTPException(status_code=400, detail=f"Role '{body.role}' is not valid for org type '{org.org_type}'. Valid roles: {valid_roles}")

    old_role = target.role
    target.role = body.role
    await db.commit()

    return {
        "user_id": str(target.id),
        "old_role": old_role,
        "new_role": body.role,
        "features": get_accessible_features(body.role),
    }


# ── Registration with Org Type ───────────────────────────────────────────────

@router.post("/register/")
async def register_with_type(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """Self-service registration — creates org + admin user based on org type."""
    org_type = body.get("org_type", "provider")
    if org_type not in ORG_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid org_type: {org_type}")

    # Check email
    email = body.get("email", "").lower()
    if (await db.execute(select(RFAUser).where(RFAUser.email == email))).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create org
    org_info = ORG_TYPES[org_type]
    org = RFAOrganization(
        id=uuid.uuid4(),
        name=body.get("org_name", body.get("practice_name", "")),
        org_type=org_type,
        w_number=body.get("w_number"),
        contact_name=body.get("name", body.get("full_name", "")),
        contact_email=email,
        contact_phone=body.get("phone"),
        is_active=True,
    )
    db.add(org)
    await db.flush()

    # Create admin user with default admin role for the org type
    admin_role = "practice_admin" if org_type == "provider" else "org_admin"
    pw_hash = bcrypt.hashpw(body.get("password", "changeme").encode(), bcrypt.gensalt()).decode()
    admin = RFAUser(
        id=uuid.uuid4(),
        org_id=org.id,
        email=email,
        full_name=body.get("name", body.get("full_name", "")),
        role=admin_role,
        password_hash=pw_hash,
        is_active=True,
    )
    db.add(admin)
    await db.commit()

    return {
        "org": {"id": str(org.id), "name": org.name, "org_type": org_type},
        "user": {"id": str(admin.id), "email": admin.email, "role": admin_role},
        "navigation": get_navigation(org_type, admin_role),
        "next_steps": [
            "Log in with your credentials",
            "Add team members from Settings",
            "Start creating cases" if org_type == "non_provider" else "Start submitting prior authorizations",
        ],
    }
