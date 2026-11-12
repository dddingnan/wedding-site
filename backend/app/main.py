from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routes import admin, health, invites
from app.core.config import get_settings
from app.core.limiter import limiter


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Wedding API", version="0.1.0")

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(health.router, prefix="/api")
    app.include_router(invites.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")
    app.include_router(admin.protected, prefix="/api")
    return app


app = create_app()
