from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from starlette.exceptions import HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.routes.hardware import router as hardware_router
from app.routes.api import router as api_router
from app.routes.pages import router as pages_router
from app.routes.auth import router as auth_router
from app.routes.audit_log import router as audit_log_router
from app.middleware.audit_logging import AuditLoggingMiddleware
from app.middleware.auth import AuthenticationMiddleware
from app.core.templates import templates

from app.audit.listeners import initialize_audit_listeners


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("App starting up 🚀")
    logger.info("Initializing audit listeners...")
    initialize_audit_listeners()
    logger.info("Audit listeners initialized.")
    yield
    logger.info("App shutting down...")


def create_app() -> FastAPI:
    app = FastAPI(title="Inventory Management System", version="1.0.0", lifespan=lifespan)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        accept_header = request.headers.get("accept", "")
        if exc.status_code == 404 and "text/html" in accept_header:
            return templates.TemplateResponse(
                "404.html", 
                {"request": request}, 
                status_code=404
            )

        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    app.add_middleware(AuthenticationMiddleware)
    app.add_middleware(AuditLoggingMiddleware)

    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    app.include_router(auth_router, prefix="")
    app.include_router(pages_router)
    app.include_router(hardware_router, prefix="/hardware")
    app.include_router(audit_log_router, prefix="")
    # app.include_router(api_router, prefix="/api", tags=["api"])

    return app
