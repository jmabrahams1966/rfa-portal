"""AIRA — Workers' Compensation RFA Submission Platform — FastAPI entry point."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .routers import all_routers

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Artificially Intelligent Resolution Application",
    version="0.1.0",
)

# CORS — wildcard for dev, locked down in production via allowed_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler — ensures CORS headers on 500 errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import logging
    logging.getLogger(__name__).exception("Unhandled error: %s", exc)
    origin = request.headers.get("origin", "")
    headers = {}
    if origin:
        headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {type(exc).__name__}: {str(exc)[:200]}"},
        headers=headers,
    )


# Register all routers
for router in all_routers:
    app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "description": "Artificially Intelligent Resolution Application",
        "status": "running",
        "environment": settings.environment,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
