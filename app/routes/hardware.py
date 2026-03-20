import json
import logging
import math
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, parse_qs

from fastapi import (
    APIRouter,
    Request,
    Depends,
    HTTPException,
    Query,
    Form,
    UploadFile,
    File,
)
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.core import db
from app.core.db import get_session
from app.core.templates import templates
from app.dependencies.auth import require_admin, require_visitor, get_current_user
from app.models.hardware import StatusEnum, ModelEnum
from app.services.hardware import HardwareService
from app.services.audit import AuditService


logger = logging.getLogger(__name__)

router = APIRouter()


def _get_filter_params(request: Request) -> Dict[str, Any]:
    current_url = request.headers.get("HX-Current-URL")

    if current_url:
        parsed = urlparse(current_url)
        raw_params = parse_qs(parsed.query)

        def get_list(name: str) -> List[str]:
            return [v for v in raw_params.get(name, []) if v]

        def get_one(name: str, default: Optional[str] = None) -> Optional[str]:
            values = raw_params.get(name)
            if not values:
                return default
            value = values[-1]
            return value or default

    else:
        raw_params = request.query_params

        def get_list(name: str) -> List[str]:
            return [v for v in raw_params.getlist(name) if v]

        def get_one(name: str, default: Optional[str] = None) -> Optional[str]:
            value = raw_params.get(name, default)
            return value or default

    def to_int(value: Optional[str], default: int) -> int:
        try:
            return int(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    return {
        "search": get_one("search"),
        "status": get_list("status") or None,
        "model": get_one("model"),
        "center": get_one("center"),
        "page": to_int(get_one("page"), 1),
        "per_page": to_int(get_one("per_page"), 20),
        "sort_by": get_one("sort_by", "updated_at") or "updated_at",
        "sort_order": get_one("sort_order", "desc") or "desc",
    }


def _render_hardware_table(
    request: Request,
    hardware_service: HardwareService,
    current_user: Dict[str, Any],
    filters: Dict[str, Any],
):
    result = hardware_service.get_hardware_list(
        search=filters["search"],
        status=filters["status"],
        model=filters["model"],
        center=filters["center"],
        page=filters["page"],
        per_page=filters["per_page"],
        sort_by=filters["sort_by"],
        sort_order=filters["sort_order"],
    )

    total_pages = result["total_pages"] or 0
    if total_pages and filters["page"] > total_pages:
        filters["page"] = total_pages
        result = hardware_service.get_hardware_list(
            search=filters["search"],
            status=filters["status"],
            model=filters["model"],
            center=filters["center"],
            page=filters["page"],
            per_page=filters["per_page"],
            sort_by=filters["sort_by"],
            sort_order=filters["sort_order"],
        )
    elif total_pages == 0 and filters["page"] != 1:
        filters["page"] = 1
        result = hardware_service.get_hardware_list(
            search=filters["search"],
            status=filters["status"],
            model=filters["model"],
            center=filters["center"],
            page=filters["page"],
            per_page=filters["per_page"],
            sort_by=filters["sort_by"],
            sort_order=filters["sort_order"],
        )

    template_data = {
        "request": request,
        "hardware_list": result["hardware_list"],
        "total_count": result["total_count"],
        "current_page": result["current_page"],
        "per_page": result["per_page"],
        "total_pages": result["total_pages"],
        "status_counts": result["status_counts"],
        "search_query": filters["search"],
        "status_filter": result["status_filter"],
        "model_filter": filters["model"],
        "center_filter": filters["center"],
        "sort_by": filters["sort_by"],
        "sort_order": filters["sort_order"],
        "current_user": current_user,
    }

    return templates.TemplateResponse("partials/hardware_table.html", template_data)


@router.get("", response_class=HTMLResponse)
async def hardware_list(
    request: Request,
    db: Session = Depends(get_session),
    current_user=Depends(require_visitor),
    search: Optional[str] = Query(None),
    status: Optional[list[str]] = Query(None),
    model: Optional[str] = Query(None),
    center: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: Optional[str] = Query("updated_at"),
    sort_order: Optional[str] = Query("desc"),
):
    try:
        hardware_service = HardwareService(db)

        result = hardware_service.get_hardware_list(
            search=search,
            status=status,
            model=model,
            center=center,
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        template_data = {
            "request": request,
            "hardware_list": result["hardware_list"],
            "total_count": result["total_count"],
            "current_page": result["current_page"],
            "per_page": result["per_page"],
            "total_pages": result["total_pages"],
            "status_counts": result["status_counts"],
            "search_query": search,
            "status_filter": result["status_filter"],
            "model_filter": model,
            "center_filter": center,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "current_user": current_user,
        }

        is_htmx = request.headers.get("HX-Request") == "true"
        if is_htmx:
            return templates.TemplateResponse(
                "partials/hardware_table.html", template_data
            )

        return templates.TemplateResponse("hardware_list.html", template_data)

    except Exception as e:
        logger.error(f"Error loading hardware list: {e}")
        raise HTTPException(status_code=500, detail="Failed to load hardware list")


@router.get("/add", response_class=HTMLResponse)
async def add_hardware_form(request: Request, current_user=Depends(require_admin)):
    return templates.TemplateResponse(
        "hardware_form.html",
        {"request": request, "hardware": None, "current_user": current_user},
    )


@router.post("/add")
async def add_hardware(
    request: Request,
    db: Session = Depends(get_session),
    current_user=Depends(require_admin),
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
    comment: Optional[str] = Form(None),
    missing: bool = Form(False),
):
    try:
        hardware_service = HardwareService(db)

        hardware_data = {
            "hostname": hostname,
            "serial_number": serial_number,
            "model": model,
            "status": status,
            "ip": ip,
            "mac": mac,
            "uuid": uuid,
            "center": center,
            "enduser": enduser,
            "ticket": ticket,
            "po_ticket": po_ticket,
            "comment": comment,
            "missing": missing,
        }

        hardware = hardware_service.create_hardware(hardware_data, current_user)

        is_htmx = request.headers.get("HX-Request") == "true"
        if is_htmx:
            response = Response(status_code=200)
            response.headers["HX-Redirect"] = f"/hardware/{hardware.id}"
            return response

        return RedirectResponse(url="/hardware", status_code=303)

    except Exception as e:
        logger.error(f"Error adding hardware: {e}")
        raise HTTPException(status_code=400, detail="Failed to add hardware")


@router.get("/import", response_class=HTMLResponse)
async def bulk_import_form(request: Request, current_user=Depends(require_admin)):
    return templates.TemplateResponse("bulk_import.html", {"request": request})


@router.post("/import")
async def bulk_import(
    request: Request,
    db: Session = Depends(get_session),
    current_user=Depends(require_admin),
    file: UploadFile = File(...),
):
    try:
        hardware_service = HardwareService(db)

        filename = file.filename.lower()
        if not (
            filename.endswith(".csv")
            or filename.endswith(".xlsx")
            or filename.endswith(".xls")
        ):
            raise HTTPException(
                status_code=400,
                detail="File must be a CSV or Excel file (.csv, .xlsx, .xls)",
            )

        contents = await file.read()

        preview = hardware_service.parse_import_file(contents, filename)

        return templates.TemplateResponse(
            "bulk_import_preview.html",
            {
                "request": request,
                "preview": preview,
                "file_name": file.filename,
            },
        )

    except ValueError as e:
        logger.error(f"Invalid file format: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error importing file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import file: {str(e)}")


@router.post("/import/confirm")
async def bulk_import_confirm(
    request: Request,
    db: Session = Depends(get_session),
    current_user=Depends(require_admin),
    payload: str = Form(...),
):
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid confirmation payload")

    valid_items = data.get("valid_items", [])
    if not valid_items:
        return templates.TemplateResponse(
            "bulk_import_results.html",
            {
                "request": request,
                "results": {
                    "total_rows": data.get("total_rows", 0),
                    "created": 0,
                    "updated": 0,
                    "errors": data.get("errors", []) + ["No valid entries to import."],
                },
            },
            status_code=400,
        )

    hardware_service = HardwareService(db)

    apply_summary = hardware_service.apply_import_data(
        [item.get("data", {}) for item in valid_items],
        current_user,
    )

    combined_errors = data.get("errors", []) + apply_summary["errors"]

    results = {
        "total_rows": data.get("total_rows", 0),
        "created": apply_summary["created"],
        "updated": apply_summary["updated"],
        "errors": combined_errors,
    }

    return templates.TemplateResponse(
        "bulk_import_results.html", {"request": request, "results": results}
    )


@router.get("/{hardware_id}/edit", response_class=HTMLResponse)
async def edit_hardware_form(
    request: Request,
    hardware_id: int,
    db: Session = Depends(get_session),
    current_user=Depends(require_admin),
):
    try:
        hardware_service = HardwareService(db)
        hardware = hardware_service.get_hardware_by_id(hardware_id)
        if not hardware:
            raise HTTPException(status_code=404, detail="Hardware not found")

        return templates.TemplateResponse(
            "hardware_form.html",
            {"request": request, "hardware": hardware, "current_user": current_user},
        )
    except Exception as e:
        logger.error(f"Error loading hardware edit form: {e}")
        raise HTTPException(status_code=500, detail="Failed to load hardware edit form")


@router.post("/{hardware_id}/edit")
async def edit_hardware(
    request: Request,
    hardware_id: int,
    db: Session = Depends(get_session),
    current_user=Depends(require_admin),
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
    comment: Optional[str] = Form(None),
    missing: bool = Form(False),
):
    try:
        hardware_service = HardwareService(db)

        hardware_data = {
            "hostname": hostname,
            "serial_number": serial_number,
            "model": model,
            "status": status,
            "ip": ip,
            "mac": mac,
            "uuid": uuid,
            "center": center,
            "enduser": enduser,
            "ticket": ticket,
            "po_ticket": po_ticket,
            "comment": comment,
            "missing": missing,
        }

        hardware = hardware_service.update_hardware(
            hardware_id, hardware_data, current_user
        )

        is_htmx = request.headers.get("HX-Request") == "true"
        if is_htmx:
            response = Response(status_code=200)
            response.headers["HX-Redirect"] = "/hardware"
            return response

        return RedirectResponse(url="/hardware", status_code=303)

    except ValueError as e:
        logger.error(f"Error editing hardware: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error editing hardware: {e}")
        raise HTTPException(status_code=400, detail="Failed to edit hardware")


@router.delete("/{hardware_id}")
async def delete_hardware(
    request: Request,
    hardware_id: int,
    db: Session = Depends(get_session),
    current_user=Depends(require_admin),
):
    try:
        hardware_service = HardwareService(db)
        hardware_service.delete_hardware(hardware_id)

        if request.headers.get("HX-Request") == "true":
            filters = _get_filter_params(request)
            return _render_hardware_table(
                request, hardware_service, current_user, filters
            )

        return RedirectResponse(url="/hardware", status_code=303)

    except ValueError as e:
        logger.error(f"Error deleting hardware: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting hardware: {e}")
        raise HTTPException(status_code=400, detail="Failed to delete hardware")


@router.get("/{hardware_id}", response_class=HTMLResponse)
async def hardware_detail(
    request: Request,
    hardware_id: int,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    try:
        hardware_service = HardwareService(db)
        hardware = hardware_service.get_hardware_by_id(hardware_id)
        if not hardware:
            raise HTTPException(status_code=404, detail="Hardware not found")

        return templates.TemplateResponse(
            "hardware_detail.html",
            {"request": request, "hardware": hardware, "current_user": current_user},
        )
    except Exception as e:
        logger.error(f"Error loading hardware detail: {e}")
        raise HTTPException(status_code=500, detail="Failed to load hardware details")


@router.get("/export/excel")
async def export_hardware_excel(
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
    search: Optional[str] = Query(None),
    status: Optional[list[str]] = Query(None),
    model: Optional[str] = Query(None),
    center: Optional[str] = Query(None),
):
    """Export hardware data to Excel format"""
    try:
        hardware_service = HardwareService(db)

        # Export data to Excel
        output = hardware_service.export_hardware_to_excel(
            search=search, status=status, model=model, center=center
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hardware_inventory_{timestamp}.xlsx"

        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except Exception as e:
        logger.error(f"Error exporting hardware to Excel: {e}")
        raise HTTPException(status_code=500, detail="Failed to export data")


@router.get("/{hardware_id}/qr")
async def generate_qr_code(
    hardware_id: int,
    db: Session = Depends(get_session),
    current_user=Depends(require_visitor),
):
    """Generate QR code for hardware detail page"""
    try:
        hardware_service = HardwareService(db)
        img_buffer, filename = hardware_service.generate_qr_code(hardware_id)

        return Response(
            content=img_buffer.getvalue(),
            media_type="image/png",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except ValueError as e:
        logger.error(f"Error generating QR code: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate QR code")


@router.get("/{hardware_id}/label")
async def generate_label_csv(
    hardware_id: int,
    db: Session = Depends(get_session),
    current_user=Depends(require_visitor),
):
    try:
        hardware_service = HardwareService(db)
        csv_string, filename = hardware_service.generate_label_csv(hardware_id)

        return Response(
            content=csv_string,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except ValueError as e:
        logger.error(f"Error generating label CSV: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating label CSV: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate label CSV")


@router.post("/{hardware_id}/status")
async def quick_status_change(
    request: Request,
    hardware_id: int,
    db: Session = Depends(get_session),
    current_user=Depends(require_admin),
    status: StatusEnum = Form(...),
):
    """Quick status change for hardware"""
    try:
        hardware_service = HardwareService(db)
        hardware = hardware_service.change_hardware_status(
            hardware_id, status, current_user
        )

        if request.headers.get("HX-Request") == "true":
            filters = _get_filter_params(request)
            return _render_hardware_table(
                request, hardware_service, current_user, filters
            )

        return {"success": True, "message": f"Status changed to {status.value}"}

    except ValueError as e:
        logger.error(f"Error changing status: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error changing status: {e}")
        raise HTTPException(status_code=500, detail="Failed to change status")


@router.post("/{hardware_id}/cycle-status")
async def cycle_status(
    request: Request,
    hardware_id: int,
    db: Session = Depends(get_session),
    current_user=Depends(require_admin),
):
    try:
        hardware_service = HardwareService(db)
        hardware, status_display = hardware_service.cycle_hardware_status(
            hardware_id, current_user
        )

        status_class = hardware.status.value.lower().replace("_", "-")

        html = f"""
        <span class="status-pill status-{status_class}" title="Status">
            <span class="status-badge status-{status_class}"></span>
            {status_display}
        </span>
        """

        return Response(content=html, media_type="text/html")

    except ValueError as e:
        logger.error(f"Error cycling status: {e}")
        if "already completed" in str(e) or "cannot be cycled" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error cycling status: {e}")
        raise HTTPException(status_code=500, detail="Failed to cycle status")


@router.get("/{hardware_id}/history", response_class=HTMLResponse)
async def hardware_history_view(
    hardware_id: int,
    request: Request,
    db: Session = Depends(get_session),
    current_user=Depends(require_admin),
    page: int = Query(1, ge=1),
):
    try:
        audit_service = AuditService(db)
        hardware_service = HardwareService(db)

        hardware_item = hardware_service.get_hardware_by_id(hardware_id)
        if not hardware_item:
            return templates.TemplateResponse(
                "404.html", {"request": request}, status_code=404
            )

        PAGE_SIZE = 15

        history_data = audit_service.get_entity_history(
            entity_name="Hardware",
            entity_id=str(hardware_id),
            page=page,
            limit=PAGE_SIZE,
        )
        if history_data is None:
            history_data = {"logs": [], "total": 0}

        total_pages = math.ceil(history_data["total"] / PAGE_SIZE)

        return templates.TemplateResponse(
            "hardware_history.html",
            {
                "request": request,
                "hardware": hardware_item,
                "history": history_data["logs"],
                "current_page": page,
                "total_pages": total_pages,
            },
        )
    except Exception as e:
        logger.error(f"Error getting entity history for Hardware {hardware_id}: {e}")

        return templates.TemplateResponse(
            "hardware_history.html",
            {
                "request": request,
                "hardware": None,
                "history": [],
                "error_message": "An error occurred while trying to load the history.",
            },
        )
