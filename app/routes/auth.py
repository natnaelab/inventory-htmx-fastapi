import logging

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.core.templates import templates
from app.core.config import settings
from app.core.db import get_session
from app.services.auth import AuthService
from app.services.user import UserService
from app.dependencies.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    current_user = get_current_user(request)
    if current_user:
        return RedirectResponse(url="/", status_code=302)
    
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error_message": request.query_params.get("error")},
    )


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_session),
):
    try:
        user_service = UserService(db)
        auth_service = AuthService()

        user_data = await run_in_threadpool(auth_service.authenticate_ad, username, password)

        if not user_data:
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error_message": "Invalid credentials or insufficient permissions. Please contact your administrator."},
                status_code=401
            )

        try:
            db_user = user_service.get_user_by_username(user_data["username"])
            if not db_user:
                db_user = user_service.create_user(
                    username=user_data["username"],
                    role=user_data["role"],
                    email=user_data.get("email"),
                    display_name=user_data.get("display_name", user_data["username"])
                )
            else:
                db_user.role = user_data["role"]
                db_user.display_name = user_data.get("display_name", db_user.display_name)
                if user_data.get("email") and not db_user.email:
                    db_user.email = user_data.get("email")

            if user_data.get("ad_object_guid"):
                user_service.update_user_from_ad(
                    user=db_user,
                    ad_object_guid=user_data.get("ad_object_guid"),
                    email=user_data.get("email")
                )
            
            user_data_with_id = user_data.copy()
            user_data_with_id["user_id"] = db_user.id

            session_token = auth_service.create_session_token(user_data_with_id)

            client_ip = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")

            user_service.update_user_login(
                user=db_user,
                session_token=session_token,
                ip_address=client_ip,
                user_agent=user_agent
            )

        except Exception as token_error:
            logger.error(f"Failed to create session token: {token_error}")
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error_message": "Session creation failed. Please try again."},
                status_code=500
            )

        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(
            key=settings.session_cookie_name,
            value=session_token,
            max_age=settings.session_expire_hours * 3600,
            httponly=True,
            secure=True,
            samesite="lax"
        )

        return response

    except Exception as e:
        logger.error(f"Login error: {e}")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error_message": "System error occurred. Please try again or contact your administrator."},
            status_code=500
        )


@router.post("/logout")
async def logout(request: Request, db: Session = Depends(get_session), current_user = Depends(get_current_user)):
    try:
        user_service = UserService(db)
        db_user = user_service.get_user_by_username(current_user["username"])
        if db_user:
            user_service.invalidate_session(db_user)
    except Exception as e:
        logger.error(f"Error during logout: {e}")
    
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=True,
        samesite="lax"
    )
    return response


@router.get("/access-denied", response_class=HTMLResponse)
async def access_denied_page(request: Request):
    return templates.TemplateResponse(
        "access_denied.html",
        {"request": request},
    )
