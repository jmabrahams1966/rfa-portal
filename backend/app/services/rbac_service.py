"""Role-Based Access Control — Provider vs Non-Provider user types with feature gating.

Organization Types:
  - provider: Surgeon practices, hospitals, medical groups
  - non_provider: Insurance carriers, TPAs, defense law firms

Roles per Org Type:

  Provider Roles:
    - practice_admin: Full access to provider features + user management
    - surgeon: Prior auth, compliance, document upload, narrative generation
    - pa_np: Same as surgeon but may need co-signature
    - medical_assistant: Document upload, case creation, limited auth access
    - billing_staff: Billing, claim status, auth status (read-only clinical)

  Non-Provider Roles:
    - org_admin: Full access to non-provider features + user management
    - adjuster: RFA filing, case management, document upload
    - attorney: RFA filing, case management, full legal features
    - paralegal: Document upload, case prep, limited filing
    - reviewer: Read-only across all org data

  Super Admin:
    - super_admin: Cross-org management, user type assignment, platform config
"""

from typing import Optional

# ── Organization Types ───────────────────────────────────────────────────────

ORG_TYPES = {
    "provider": {
        "name": "Healthcare Provider",
        "description": "Surgeon practices, hospitals, and medical groups",
        "subtypes": ["solo_practice", "group_practice", "hospital", "ambulatory_surgery_center"],
        "roles": ["practice_admin", "surgeon", "pa_np", "medical_assistant", "billing_staff"],
        "default_role": "surgeon",
    },
    "non_provider": {
        "name": "Insurance / Legal",
        "description": "Insurance carriers, TPAs, self-insured employers, and defense law firms",
        "subtypes": ["carrier", "tpa", "self_insured", "law_firm"],
        "roles": ["org_admin", "adjuster", "attorney", "paralegal", "reviewer"],
        "default_role": "adjuster",
    },
}

# ── Role Definitions ─────────────────────────────────────────────────────────

ROLES = {
    # Super Admin
    "super_admin": {
        "name": "Super Admin",
        "org_type": None,  # Cross-org
        "level": 100,
        "description": "Platform-wide administration",
    },
    # Provider Roles
    "practice_admin": {
        "name": "Practice Administrator",
        "org_type": "provider",
        "level": 90,
        "description": "Full provider access plus user and practice management",
    },
    "surgeon": {
        "name": "Surgeon / Physician",
        "org_type": "provider",
        "level": 80,
        "description": "Prior auth submission, compliance checking, narrative review and sign-off",
    },
    "pa_np": {
        "name": "PA / NP",
        "org_type": "provider",
        "level": 70,
        "description": "Prior auth preparation, document upload, may require co-signature",
    },
    "medical_assistant": {
        "name": "Medical Assistant",
        "org_type": "provider",
        "level": 50,
        "description": "Document upload, case creation, data entry",
    },
    "billing_staff": {
        "name": "Billing Staff",
        "org_type": "provider",
        "level": 40,
        "description": "Auth status tracking, billing, claim follow-up",
    },
    # Non-Provider Roles
    "org_admin": {
        "name": "Organization Admin",
        "org_type": "non_provider",
        "level": 90,
        "description": "Full non-provider access plus user and org management",
    },
    "adjuster": {
        "name": "Claims Adjuster",
        "org_type": "non_provider",
        "level": 80,
        "description": "RFA filing, case management, document upload, status tracking",
    },
    "attorney": {
        "name": "Attorney",
        "org_type": "non_provider",
        "level": 80,
        "description": "RFA filing, case management, legal document management",
    },
    "paralegal": {
        "name": "Paralegal",
        "org_type": "non_provider",
        "level": 50,
        "description": "Document preparation, case setup, limited filing",
    },
    "reviewer": {
        "name": "Reviewer",
        "org_type": "non_provider",
        "level": 20,
        "description": "Read-only access to org data",
    },
    # Legacy/generic
    "admin": {
        "name": "Admin",
        "org_type": None,
        "level": 90,
        "description": "Generic admin (legacy)",
    },
    "read_only": {
        "name": "Read Only",
        "org_type": None,
        "level": 10,
        "description": "Read-only access",
    },
}

# ── Feature Access Matrix ────────────────────────────────────────────────────
# Maps features to which roles can access them

FEATURE_ACCESS = {
    # ── Provider-Side Features ───────────────────────────────────────
    "prior_auth.create": ["practice_admin", "surgeon", "pa_np", "medical_assistant", "super_admin"],
    "prior_auth.submit": ["practice_admin", "surgeon", "pa_np", "super_admin"],
    "prior_auth.sign": ["practice_admin", "surgeon", "super_admin"],  # Only physicians sign
    "prior_auth.view": ["practice_admin", "surgeon", "pa_np", "medical_assistant", "billing_staff", "super_admin"],
    "prior_auth.upload_docs": ["practice_admin", "surgeon", "pa_np", "medical_assistant", "super_admin"],
    "prior_auth.generate_narrative": ["practice_admin", "surgeon", "pa_np", "super_admin"],
    "prior_auth.edit_narrative": ["practice_admin", "surgeon", "pa_np", "super_admin"],
    "prior_auth.denial_management": ["practice_admin", "surgeon", "pa_np", "billing_staff", "super_admin"],
    "prior_auth.peer_to_peer": ["practice_admin", "surgeon", "super_admin"],  # Only physicians do P2P
    "prior_auth.analytics": ["practice_admin", "surgeon", "billing_staff", "super_admin"],

    "compliance.check": ["practice_admin", "surgeon", "pa_np", "super_admin"],
    "compliance.view_guidelines": ["practice_admin", "surgeon", "pa_np", "medical_assistant", "billing_staff", "super_admin"],
    "compliance.ai_review": ["practice_admin", "surgeon", "pa_np", "super_admin"],

    "payer_guidelines.view": ["practice_admin", "surgeon", "pa_np", "billing_staff", "super_admin"],

    # ── Non-Provider-Side Features ───────────────────────────────────
    "rfa_1lc.create": ["org_admin", "adjuster", "attorney", "paralegal", "super_admin"],
    "rfa_1lc.submit": ["org_admin", "adjuster", "attorney", "super_admin"],
    "rfa_1lc.view": ["org_admin", "adjuster", "attorney", "paralegal", "reviewer", "super_admin"],
    "rfa_1lc.upload_docs": ["org_admin", "adjuster", "attorney", "paralegal", "super_admin"],
    "rfa_1lc.ai_extraction": ["org_admin", "adjuster", "attorney", "super_admin"],
    "rfa_1lc.batch_filing": ["org_admin", "adjuster", "super_admin"],

    "rfa_2.create": ["org_admin", "adjuster", "attorney", "super_admin"],
    "rfa_2.submit": ["org_admin", "adjuster", "attorney", "super_admin"],
    "rfa_2.view": ["org_admin", "adjuster", "attorney", "paralegal", "reviewer", "super_admin"],

    "case.create": ["practice_admin", "surgeon", "pa_np", "medical_assistant",
                     "org_admin", "adjuster", "attorney", "paralegal", "super_admin"],
    "case.view": ["practice_admin", "surgeon", "pa_np", "medical_assistant", "billing_staff",
                   "org_admin", "adjuster", "attorney", "paralegal", "reviewer", "super_admin"],
    "case.edit": ["practice_admin", "surgeon", "pa_np",
                   "org_admin", "adjuster", "attorney", "super_admin"],

    # ── Shared Features ──────────────────────────────────────────────
    "dashboard.view": ["practice_admin", "surgeon", "pa_np", "medical_assistant", "billing_staff",
                        "org_admin", "adjuster", "attorney", "paralegal", "reviewer", "super_admin"],
    "analytics.view": ["practice_admin", "surgeon", "billing_staff",
                         "org_admin", "adjuster", "attorney", "super_admin"],
    "documents.upload": ["practice_admin", "surgeon", "pa_np", "medical_assistant",
                          "org_admin", "adjuster", "attorney", "paralegal", "super_admin"],
    "documents.view": ["practice_admin", "surgeon", "pa_np", "medical_assistant", "billing_staff",
                         "org_admin", "adjuster", "attorney", "paralegal", "reviewer", "super_admin"],

    # ── Enterprise Features ──────────────────────────────────────────
    "batch.import": ["org_admin", "adjuster", "super_admin"],
    "batch.submit": ["org_admin", "adjuster", "super_admin"],
    "workflow.assign": ["practice_admin", "org_admin", "super_admin"],
    "workflow.approve": ["practice_admin", "org_admin", "super_admin"],
    "deadline.view": ["practice_admin", "surgeon", "pa_np", "billing_staff",
                       "org_admin", "adjuster", "attorney", "paralegal", "super_admin"],
    "deadline.manage": ["practice_admin", "org_admin", "super_admin"],
    "attorney_intel.view": ["org_admin", "adjuster", "attorney", "super_admin"],
    "narrative_ai.optimize": ["org_admin", "adjuster", "attorney",
                               "practice_admin", "surgeon", "pa_np", "super_admin"],
    "billing.view": ["org_admin", "adjuster", "billing_staff", "super_admin"],
    "billing.manage": ["org_admin", "super_admin"],
    "compliance_report.view": ["practice_admin", "org_admin", "super_admin"],
    "ocr.use": ["practice_admin", "surgeon", "pa_np", "medical_assistant",
                 "org_admin", "adjuster", "attorney", "paralegal", "super_admin"],

    # ── Admin Features ───────────────────────────────────────────────
    "users.manage": ["practice_admin", "org_admin", "super_admin"],
    "users.view": ["practice_admin", "org_admin", "super_admin"],
    "org.settings": ["practice_admin", "org_admin", "super_admin"],
    "super_admin.manage_orgs": ["super_admin"],
    "super_admin.manage_users": ["super_admin"],
    "super_admin.set_org_type": ["super_admin"],
    "super_admin.view_all": ["super_admin"],
}

# ── Navigation Menu per Org Type ─────────────────────────────────────────────

NAVIGATION = {
    "provider": [
        {"path": "/dashboard", "label": "Dashboard", "icon": "📊", "feature": "dashboard.view"},
        {"path": "/prior-auth", "label": "Prior Authorizations", "icon": "📋", "feature": "prior_auth.view"},
        {"path": "/compliance", "label": "Compliance Checker", "icon": "✅", "feature": "compliance.check"},
        {"path": "/cases", "label": "Cases", "icon": "📁", "feature": "case.view"},
        {"path": "/guidelines", "label": "Payer Guidelines", "icon": "📖", "feature": "payer_guidelines.view"},
        {"path": "/analytics", "label": "Analytics", "icon": "📈", "feature": "analytics.view"},
        {"path": "/settings", "label": "Settings", "icon": "⚙️", "feature": "org.settings"},
    ],
    "non_provider": [
        {"path": "/dashboard", "label": "Dashboard", "icon": "📊", "feature": "dashboard.view"},
        {"path": "/cases", "label": "Cases", "icon": "📁", "feature": "case.view"},
        {"path": "/submissions", "label": "RFA Filings", "icon": "📄", "feature": "rfa_1lc.view"},
        {"path": "/batch", "label": "Batch Filing", "icon": "📦", "feature": "batch.import"},
        {"path": "/deadlines", "label": "Deadlines", "icon": "⏰", "feature": "deadline.view"},
        {"path": "/attorneys", "label": "Attorney Intel", "icon": "⚖️", "feature": "attorney_intel.view"},
        {"path": "/analytics", "label": "Analytics", "icon": "📈", "feature": "analytics.view"},
        {"path": "/billing", "label": "Billing", "icon": "💰", "feature": "billing.view"},
        {"path": "/settings", "label": "Settings", "icon": "⚙️", "feature": "org.settings"},
    ],
    "super_admin": [
        {"path": "/dashboard", "label": "Platform Dashboard", "icon": "📊", "feature": "dashboard.view"},
        {"path": "/organizations", "label": "Organizations", "icon": "🏢", "feature": "super_admin.manage_orgs"},
        {"path": "/users", "label": "All Users", "icon": "👥", "feature": "super_admin.manage_users"},
        {"path": "/analytics", "label": "Platform Analytics", "icon": "📈", "feature": "super_admin.view_all"},
        {"path": "/settings", "label": "Platform Settings", "icon": "⚙️", "feature": "super_admin.manage_orgs"},
    ],
}


# ── Access Control Functions ─────────────────────────────────────────────────

def has_access(role: str, feature: str) -> bool:
    """Check if a role has access to a specific feature."""
    allowed_roles = FEATURE_ACCESS.get(feature, [])
    return role in allowed_roles


def get_accessible_features(role: str) -> list[str]:
    """Get all features accessible to a role."""
    return [feature for feature, roles in FEATURE_ACCESS.items() if role in roles]


def get_navigation(org_type: str, role: str) -> list[dict]:
    """Get navigation menu items for a user based on org type and role."""
    if role == "super_admin":
        nav = NAVIGATION.get("super_admin", [])
    else:
        nav = NAVIGATION.get(org_type, [])

    return [item for item in nav if has_access(role, item["feature"])]


def get_roles_for_org_type(org_type: str) -> list[dict]:
    """Get available roles for an organization type."""
    org = ORG_TYPES.get(org_type, {})
    role_keys = org.get("roles", [])
    return [{"key": k, **ROLES[k]} for k in role_keys if k in ROLES]


def validate_role_for_org(role: str, org_type: str) -> bool:
    """Check if a role is valid for a given org type."""
    if role == "super_admin":
        return True
    org = ORG_TYPES.get(org_type, {})
    return role in org.get("roles", [])


def get_org_type_info(org_type: str) -> dict:
    """Get info about an organization type."""
    return ORG_TYPES.get(org_type, {})


def get_user_context(user, org) -> dict:
    """Build the full user context for frontend rendering."""
    role = user.role if hasattr(user, 'role') else 'reviewer'
    org_type = org.org_type if org and hasattr(org, 'org_type') else 'non_provider'

    return {
        "user_id": str(user.id) if hasattr(user, 'id') else None,
        "email": getattr(user, 'email', ''),
        "full_name": getattr(user, 'full_name', ''),
        "role": role,
        "role_info": ROLES.get(role, {}),
        "org_type": org_type,
        "org_type_info": ORG_TYPES.get(org_type, {}),
        "is_provider": org_type == "provider",
        "is_non_provider": org_type == "non_provider",
        "is_super_admin": role == "super_admin",
        "navigation": get_navigation(org_type, role),
        "features": get_accessible_features(role),
    }
