from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, status
from app.core.config import settings
from app.services.auth import AuthService, UserRole
import logging

logger = logging.getLogger(__name__)


def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    try:
        session_token = request.cookies.get(settings.session_cookie_name)
        if not session_token:
            return None
        
        auth_service = AuthService()        
        payload = auth_service.verify_session_token(session_token)

        if not payload:
            return None

        user_data = {
            "username": payload.get("username"),
            "role": payload.get("role")
        }
        request.state.user = user_data
        return user_data

    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        return None


def require_authentication(request: Request) -> Dict[str, Any]:
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            detail="Redirect to login",
            headers={"Location": f"/login?next={request.url.path}"}
        )
    return current_user


def require_admin(request: Request) -> Dict[str, Any]:
    current_user = require_authentication(request)
    
    if current_user["role"] != UserRole.ADMINISTRATOR:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            detail="Redirect to access denied",
            headers={"Location": "/access-denied"}
        )
    
    return current_user


def require_visitor(request: Request) -> Dict[str, Any]:
    current_user = require_authentication(request)

    if current_user["role"] not in [UserRole.VISITOR, UserRole.ADMINISTRATOR]:
        raise HTTPException(
            status_code=status.HTTP_302_FOUND,
            detail="Redirect to access denied",
            headers={"Location": "/access-denied"}
        )

    return current_user
