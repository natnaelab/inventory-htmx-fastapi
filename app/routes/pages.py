from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.core.templates import templates
from app.models.hardware import Hardware, StatusEnum
from app.services.stock import StockService
from app.dependencies.auth import require_visitor

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_session), current_user = Depends(require_visitor)):
    status_counts: Dict[str, int] = {}
    for status in StatusEnum:
        count = db.query(Hardware).filter(Hardware.status == status).count()
        status_counts[status.value] = count

    total_count = db.query(Hardware).count()

    recent_hardware = db.query(Hardware).order_by(Hardware.updated_at.desc()).limit(10).all()

    current_page = 1
    per_page = 20
    offset = (current_page - 1) * per_page

    default_statuses = [s for s in StatusEnum if s != StatusEnum.COMPLETED]
    hardware_list = db.query(Hardware).filter(Hardware.status.in_(default_statuses)).order_by(Hardware.updated_at.desc()).offset(offset).limit(per_page).all()
    filtered_count = db.query(Hardware).filter(Hardware.status.in_(default_statuses)).count()
    total_pages = (filtered_count + per_page - 1) // per_page

    stock_service = StockService(db)
    stock_summary = stock_service.get_stock_summary()

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
            "status_filter": [s.value for s in default_statuses],
            "model_filter": None,
            "center_filter": None,
            "status_counts": status_counts,
            "recent_hardware": recent_hardware,
            "stock_summary": stock_summary,
            "current_user": current_user
        },
    )


@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
