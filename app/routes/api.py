from typing import Dict

from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.core.templates import templates
from app.models.hardware import Hardware, StatusEnum

router = APIRouter()
