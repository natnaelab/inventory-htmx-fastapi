from contextlib import asynccontextmanager
import logging
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes.hardware import router as hardware_router
from app.routes.api import router as api_router
from app.routes.pages import router as pages_router

logger = logging.getLogger(__name__)


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     pass


def create_app() -> FastAPI:
    app = FastAPI(title="Inventory Management System", version="1.0.0", 
                #   lifespan=lifespan
                  )

    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    app.include_router(pages_router)
    app.include_router(hardware_router, prefix="")
    # app.include_router(api_router, prefix="/api", tags=["api"])

    return app
