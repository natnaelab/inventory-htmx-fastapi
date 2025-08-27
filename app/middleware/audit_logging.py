import time
import logging
from datetime import datetime, timezone
from typing import Callable
from fastapi import Request, Response, BackgroundTasks
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.models.audit_log import AuditLog
from app.dependencies.auth import get_current_user
from app.audit.context import audit_context

logger = logging.getLogger(__name__)


def log_to_database(log_data: dict):
    db: Session = SessionLocal()
    try:
        current_user = log_data.pop("current_user", None)
        user_id = None
        username = None

        if current_user:
            username = current_user.get("username")
            user_id = current_user.get("user_id")

        audit_log = AuditLog(**log_data, user_id=user_id, username=username, timestamp=datetime.now(timezone.utc))
        db.add(audit_log)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to save audit log: {e}")
        db.rollback()
    finally:
        db.close()


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, skip_paths: list = None):
        super().__init__(app)
        self.skip_paths = skip_paths or ["/static/", "/docs", "/redoc", "/openapi.json", "/health", "/favicon.ico"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if any(request.url.path.startswith(skip) for skip in self.skip_paths):
            return await call_next(request)

        current_user = get_current_user(request)
        context_data = {
            "method": request.method,
            "path": request.url.path,
            "remote_addr": self._get_client_ip(request),
            "user_id": current_user.get("user_id") if current_user else None,
            "username": current_user.get("username") if current_user else None,
            "user_agent": request.headers.get("user-agent"),
            "status_code": 500,
        }

        token = audit_context.set(context_data)

        start_time = time.time()
        error_message = None
        status_code = 500
        request_body_bytes = await request.body()
        request_body_size = len(request_body_bytes) if request_body_bytes else 0

        async def receive():
            return {"type": "http.request", "body": request_body_bytes}

        request._receive = receive

        response_body_size = 0

        try:
            response = await call_next(request)
            status_code = response.status_code
            context_data["status_code"] = status_code
            audit_context.set(context_data)

            if "context-length" in response.headers:
                try:
                    response_body_size = int(response.headers["context-length"])
                except (ValueError, TypeError):
                    response_body_size = 0

        except Exception as e:
            error_message = str(e)
            response = Response(content="Internal Server Error", status_code=500)
            logger.error(f"Error processing request {request.method} {request.url.path}: {error_message}")
        finally:
            response_time_ms = (time.time() - start_time) * 1000

            log_data_for_access_log = {
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params) if request.query_params else None,
                "user_agent": request.headers.get("user-agent"),
                "remote_addr": self._get_client_ip(request),
                "status_code": status_code,
                "response_time_ms": response_time_ms,
                "error_message": error_message,
                "request_body_size": request_body_size,
                "response_body_size": response_body_size,
                "current_user": current_user,
            }

            if getattr(response, "background", None) is None:
                response.background = BackgroundTasks()
            response.background.add_task(log_to_database, log_data=log_data_for_access_log)

            audit_context.reset(token)

        return response

    def _get_client_ip(self, request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"
