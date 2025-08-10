from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.core.templates import templates
from app.models.hardware import Hardware, StatusEnum

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_session)):
    total_count = db.query(Hardware).count()

    status_counts: Dict[str, int] = {}
    for status in StatusEnum:
        count = db.query(Hardware).filter(Hardware.status == status).count()
        status_counts[status.value] = count

    recent_hardware = db.query(Hardware).order_by(Hardware.updated_at.desc()).limit(10).all()

    current_page = 1
    per_page = 20
    offset = (current_page - 1) * per_page
    hardware_list = db.query(Hardware).order_by(Hardware.updated_at.desc()).offset(offset).limit(per_page).all()
    total_pages = (total_count + per_page - 1) // per_page

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "hardware_list": hardware_list,
            "total_count": total_count,
            "current_page": current_page,
            "per_page": per_page,
            "total_pages": total_pages,
            "search_query": None,
            "status_filter": None,
            "model_filter": None,
            "center_filter": None,
            "status_counts": status_counts,
            "recent_hardware": recent_hardware,
            "current_year": datetime.now().year,
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
    )


@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
