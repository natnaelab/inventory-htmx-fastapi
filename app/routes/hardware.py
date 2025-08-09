from datetime import datetime, timezone
from typing import Optional
import logging

from fastapi import APIRouter, Request, Depends, HTTPException, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.core.templates import templates
from app.models.hardware import Hardware, StatusEnum, ModelEnum

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/hardware", response_class=HTMLResponse)
async def hardware_list(
    request: Request,
    db: Session = Depends(get_session),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    center: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):

    query = db.query(Hardware)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Hardware.hostname.ilike(search_term))
            | (Hardware.ip.ilike(search_term))
            | (Hardware.mac.ilike(search_term))
            | (Hardware.serial_number.ilike(search_term))
            | (Hardware.uuid.ilike(search_term))
            | (Hardware.enduser.ilike(search_term))
            | (Hardware.ticket.ilike(search_term))
        )

    if status:
        try:
            status_enum = StatusEnum(status)
            query = query.filter(Hardware.status == status_enum)
        except ValueError:
            pass

    if model:
        try:
            model_enum = ModelEnum(model)
            query = query.filter(Hardware.model == model_enum)
        except ValueError:
            pass

    if center:
        query = query.filter(Hardware.center.ilike(f"%{center}%"))

    total_count = query.count()

    # Apply pagination
    offset = (page - 1) * per_page
    hardware_list = query.order_by(Hardware.updated_at.desc()).offset(offset).limit(per_page).all()

    total_pages = (total_count + per_page - 1) // per_page

    status_counts = {}
    for s in StatusEnum:
        count = db.query(Hardware).filter(Hardware.status == s).count()
        status_counts[s.value] = count

    template_data = {
        "request": request,
        "hardware_list": hardware_list,
        "total_count": total_count,
        "current_page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "status_counts": status_counts,
        "search_query": search,
        "status_filter": status,
        "model_filter": model,
        "center_filter": center,
        "current_year": datetime.now().year,
    }

    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        return templates.TemplateResponse("partials/hardware_table.html", template_data)

    return templates.TemplateResponse("hardware_list.html", template_data)


@router.get("/hardware/add", response_class=HTMLResponse)
async def add_hardware_form(request: Request):
    return templates.TemplateResponse(
        "hardware_form.html", {"request": request, "hardware": None, "current_year": datetime.now().year}
    )


@router.post("/hardware/add")
async def add_hardware(
    request: Request,
    db: Session = Depends(get_session),
    hostname: str = Form(...),
    serial_number: str = Form(...),
    model: ModelEnum = Form(...),
    status: StatusEnum = Form(...),
    ip: Optional[str] = Form(None),
    mac: Optional[str] = Form(None),
    uuid: Optional[str] = Form(None),
    center: Optional[str] = Form(None),
    enduser: Optional[str] = Form(None),
    ticket: Optional[str] = Form(None),
    po_ticket: Optional[str] = Form(None),
    admin: str = Form(...),
    comment: Optional[str] = Form(None),
    missing: bool = Form(False),
):
    try:
        now = datetime.now(timezone.utc)

        hardware = Hardware(
            hostname=hostname,
            serial_number=serial_number,
            model=model,
            status=status,
            ip=ip,
            mac=mac,
            uuid=uuid,
            center=center,
            enduser=enduser,
            ticket=ticket,
            po_ticket=po_ticket,
            admin=admin,
            comment=comment,
            missing=missing,
            created_at=now,
            updated_at=now,
            shipped_at=now if status == StatusEnum.SHIPPED else None,
        )

        db.add(hardware)
        db.commit()
        db.refresh(hardware)

        is_htmx = request.headers.get("HX-Request") == "true"
        if is_htmx:
            response = Response(status_code=200)
            response.headers["HX-Redirect"] = "/hardware"
            return response

        return RedirectResponse(url="/hardware", status_code=303)

    except Exception as e:
        logger.error(f"Error adding hardware: {e}")
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to add hardware")


@router.get("/hardware/{hardware_id}/edit", response_class=HTMLResponse)
async def edit_hardware_form(request: Request, hardware_id: int, db: Session = Depends(get_session)):
    hardware = db.query(Hardware).filter(Hardware.id == hardware_id).first()
    if not hardware:
        raise HTTPException(status_code=404, detail="Hardware not found")

    return templates.TemplateResponse(
        "hardware_form.html", {"request": request, "hardware": hardware, "current_year": datetime.now().year}
    )


@router.post("/hardware/{hardware_id}/edit")
async def edit_hardware(
    request: Request,
    hardware_id: int,
    db: Session = Depends(get_session),
    hostname: str = Form(...),
    serial_number: str = Form(...),
    model: ModelEnum = Form(...),
    status: StatusEnum = Form(...),
    ip: Optional[str] = Form(None),
    mac: Optional[str] = Form(None),
    uuid: Optional[str] = Form(None),
    center: Optional[str] = Form(None),
    enduser: Optional[str] = Form(None),
    ticket: Optional[str] = Form(None),
    po_ticket: Optional[str] = Form(None),
    admin: str = Form(...),
    comment: Optional[str] = Form(None),
    missing: bool = Form(False),
):
    hardware = db.query(Hardware).filter(Hardware.id == hardware_id).first()
    if not hardware:
        raise HTTPException(status_code=404, detail="Hardware not found")

    try:
        old_status = hardware.status

        hardware.hostname = hostname
        hardware.serial_number = serial_number
        hardware.model = model
        hardware.status = status
        hardware.ip = ip
        hardware.mac = mac
        hardware.uuid = uuid
        hardware.center = center
        hardware.enduser = enduser
        hardware.ticket = ticket
        hardware.po_ticket = po_ticket
        hardware.admin = admin
        hardware.comment = comment
        hardware.missing = missing
        hardware.updated_at = datetime.now(timezone.utc)

        if status == StatusEnum.SHIPPED and old_status != StatusEnum.SHIPPED:
            hardware.shipped_at = datetime.now(timezone.utc)

        db.commit()
        is_htmx = request.headers.get("HX-Request") == "true"
        if is_htmx:
            response = Response(status_code=200)
            response.headers["HX-Redirect"] = "/hardware"
            return response

        return RedirectResponse(url="/hardware", status_code=303)

    except Exception as e:
        logger.error(f"Error editing hardware: {e}")
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to edit hardware")


@router.delete("/hardware/{hardware_id}")
async def delete_hardware(request: Request, hardware_id: int, db: Session = Depends(get_session)):
    hardware = db.query(Hardware).filter(Hardware.id == hardware_id).first()
    if not hardware:
        raise HTTPException(status_code=404, detail="Hardware not found")

    try:
        db.delete(hardware)
        db.commit()

        # Return updated table for HTMX
        return templates.TemplateResponse(
            "partials/hardware_table.html",
            {
                "request": request,
                "hardware_list": db.query(Hardware).order_by(Hardware.updated_at.desc()).all(),
                "total_count": db.query(Hardware).count(),
                "current_page": 1,
                "per_page": 20,
                "total_pages": 1,
            },
        )

    except Exception as e:
        logger.error(f"Error deleting hardware: {e}")
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to delete hardware")


@router.get("/hardware/{hardware_id}", response_class=HTMLResponse)
async def hardware_detail(request: Request, hardware_id: int, db: Session = Depends(get_session)):
    hardware = db.query(Hardware).filter(Hardware.id == hardware_id).first()
    if not hardware:
        raise HTTPException(status_code=404, detail="Hardware not found")
    return templates.TemplateResponse(
        "hardware_detail.html",
        {
            "request": request,
            "hardware": hardware,
            "current_year": datetime.now().year,
        },
    )
