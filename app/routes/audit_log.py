import logging
from urllib.request import Request
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse

from app.core.templates import templates
from app.core.db import get_session
from app.services.audit import AuditService
from app.dependencies.auth import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit/")


@router.get("/logs", response_class=HTMLResponse)
async def audit_logs_view(request: Request, db: Session = Depends(get_session), current_user=Depends(require_admin)):
    try:
        audit_service = AuditService(db)

        stats = audit_service.get_log_statistics(30)
        if stats is None:
            stats = {
                "period_days": 30,
                "total_requests": 0,
                "error_count": 0,
                "error_rate": 0,
                "avg_response_time_ms": 0,
                "status_codes": {},
                "top_endpoints": [],
            }

        recent_errors = audit_service.get_recent_errors(20)
        if recent_errors is None:
            recent_errors = []

        return templates.TemplateResponse(
            "admin_audit_logs.html", {"request": request, "stats": stats, "recent_errors": recent_errors}
        )

    except Exception as e:
        logger.error(f"Error loading audit logs: {e}")
        return templates.TemplateResponse(
            "admin_audit_logs.html",
            {
                "request": request,
                "stats": {
                    "period_days": 30,
                    "total_requests": 0,
                    "error_count": 0,
                    "error_rate": 0,
                    "avg_response_time_ms": 0,
                    "status_codes": {},
                    "top_endpoints": [],
                },
                "recent_errors": [],
                "error_message": f"Error loading audit logs: {str(e)}",
            },
        )
