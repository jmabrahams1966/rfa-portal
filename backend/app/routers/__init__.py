"""RFA-2 Portal — API routers."""
from .auth import router as auth_router
from .cases import router as cases_router
from .submissions import router as submissions_router
from .documents import router as documents_router
from .dashboard import router as dashboard_router
from .onboarding import router as onboarding_router
from .enterprise import router as enterprise_router
from .provider_auth import router as provider_auth_router

all_routers = [
    auth_router,
    cases_router,
    submissions_router,
    documents_router,
    dashboard_router,
    onboarding_router,
    enterprise_router,
    provider_auth_router,
]
