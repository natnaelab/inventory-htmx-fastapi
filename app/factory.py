from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes.hardware import router as hardware_router
from app.routes.api import router as api_router
from app.routes.pages import router as pages_router
from app.routes.auth import router as auth_router
from app.middleware.logging import AuditLoggingMiddleware
from app.middleware.auth import AuthenticationMiddleware

logger = logging.getLogger(__name__)


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     pass


def create_app() -> FastAPI:
    app = FastAPI(title="Inventory Management System", version="1.0.0", 
                #   lifespan=lifespan
                  )

    app.add_middleware(AuthenticationMiddleware)
    app.add_middleware(AuditLoggingMiddleware)

    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    app.include_router(auth_router, prefix="")
    app.include_router(pages_router)
    app.include_router(hardware_router, prefix="")
    # app.include_router(api_router, prefix="/api", tags=["api"])

    return app
