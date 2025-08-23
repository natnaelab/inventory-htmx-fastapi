from typing import Callable, List, Optional
from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.services.auth import AuthService
import logging

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    DEFAULT_PUBLIC_PATHS = [
        '/login',
        '/logout', 
        '/static/',
        '/health',
        '/favicon.ico',
        '/access-denied'
    ]
    
    def __init__(self, app, public_paths: Optional[List[str]] = None):
        super().__init__(app)
        self.public_paths = public_paths or self.DEFAULT_PUBLIC_PATHS
    
    def _is_public_path(self, path: str) -> bool:
        return any(
            path.startswith(public_path) if public_path.endswith('/') else path == public_path
            for public_path in self.public_paths
        )

    def _set_user_state(self, request: Request, payload: dict) -> None:
        request.state.user = {
            "user_id": payload.get('user_id'),
            "username": payload.get('username'),
            "role": payload.get('role')
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if self._is_public_path(request.url.path):
            return await call_next(request)

        session_token = request.cookies.get(settings.session_cookie_name)

        if session_token:
            auth_service = AuthService()
            
            payload = auth_service.verify_session_token(session_token)
            if payload:
                self._set_user_state(request, payload)
                return await call_next(request)

        return RedirectResponse(
                url=f"/login?next={request.url.path}", 
                status_code=302
            )
