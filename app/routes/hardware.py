import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Depends, HTTPException, Query, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.core.templates import templates
from app.dependencies.auth import require_admin, require_visitor, get_current_user
from app.models.hardware import StatusEnum, ModelEnum
from app.services.hardware import HardwareService
from app.services.audit import AuditService


logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/hardware", response_class=HTMLResponse)
async def hardware_list(
    request: Request,
    db: Session = Depends(get_session),
    current_user = Depends(get_current_user),
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
            sort_order=sort_order
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
            "current_user": current_user
        }

        is_htmx = request.headers.get("HX-Request") == "true"
        if is_htmx:
            return templates.TemplateResponse("partials/hardware_table.html", template_data)

        return templates.TemplateResponse("hardware_list.html", template_data)

    except Exception as e:
        logger.error(f"Error loading hardware list: {e}")
        raise HTTPException(status_code=500, detail="Failed to load hardware list")


@router.get("/hardware/add", response_class=HTMLResponse)
async def add_hardware_form(request: Request, current_user = Depends(require_admin)):
    return templates.TemplateResponse(
        "hardware_form.html", {"request": request, "hardware": None, "current_user": current_user}
    )

@router.post("/hardware/add")
async def add_hardware(
    request: Request,
    db: Session = Depends(get_session),
    current_user = Depends(require_admin),
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
            'hostname': hostname,
            'serial_number': serial_number,
            'model': model,
            'status': status,
            'ip': ip,
            'mac': mac,
            'uuid': uuid,
            'center': center,
            'enduser': enduser,
            'ticket': ticket,
            'po_ticket': po_ticket,
            'comment': comment,
            'missing': missing,
        }

        hardware = hardware_service.create_hardware(hardware_data, current_user)
        
        is_htmx = request.headers.get("HX-Request") == "true"
        if is_htmx:
            response = Response(status_code=200)
            response.headers["HX-Redirect"] = "/hardware"
            return response
        
        return RedirectResponse(url="/hardware", status_code=303)
        
    except Exception as e:
        logger.error(f"Error adding hardware: {e}")
        raise HTTPException(status_code=400, detail="Failed to add hardware")


@router.get("/hardware/{hardware_id}/edit", response_class=HTMLResponse)
async def edit_hardware_form(request: Request, hardware_id: int, db: Session = Depends(get_session), current_user = Depends(require_admin)):
    try:
        hardware_service = HardwareService(db)
        hardware = hardware_service.get_hardware_by_id(hardware_id)
        if not hardware:
            raise HTTPException(status_code=404, detail="Hardware not found")

        return templates.TemplateResponse(
            "hardware_form.html", {"request": request, "hardware": hardware, "current_user": current_user}
        )
    except Exception as e:
        logger.error(f"Error loading hardware edit form: {e}")
        raise HTTPException(status_code=500, detail="Failed to load hardware edit form")


@router.post("/hardware/{hardware_id}/edit")
async def edit_hardware(
    request: Request,
    hardware_id: int,
    db: Session = Depends(get_session),
    current_user = Depends(require_admin),
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
            'hostname': hostname,
            'serial_number': serial_number,
            'model': model,
            'status': status,
            'ip': ip,
            'mac': mac,
            'uuid': uuid,
            'center': center,
            'enduser': enduser,
            'ticket': ticket,
            'po_ticket': po_ticket,
            'comment': comment,
            'missing': missing,
        }
        
        hardware = hardware_service.update_hardware(hardware_id, hardware_data, current_user)
        
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


@router.delete("/hardware/{hardware_id}")
async def delete_hardware(request: Request, hardware_id: int, db: Session = Depends(get_session), current_user = Depends(require_admin)):
    try:
        hardware_service = HardwareService(db)
        hardware_service.delete_hardware(hardware_id)

        result = hardware_service.get_hardware_list(page=1, per_page=20, sort_by="updated_at", sort_order="desc")

        return templates.TemplateResponse(
            "partials/hardware_table.html",
            {
                "request": request,
                "hardware_list": result["hardware_list"],
                "total_count": result["total_count"],
                "current_page": result["current_page"],
                "per_page": result["per_page"],
                "total_pages": result["total_pages"],
                "current_user": current_user
            },
        )
        
    except ValueError as e:
        logger.error(f"Error deleting hardware: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting hardware: {e}")
        raise HTTPException(status_code=400, detail="Failed to delete hardware")


@router.get("/hardware/{hardware_id}", response_class=HTMLResponse)
async def hardware_detail(request: Request, hardware_id: int, db: Session = Depends(get_session), current_user = Depends(get_current_user)):
    try:
        hardware_service = HardwareService(db)
        hardware = hardware_service.get_hardware_by_id(hardware_id)
        if not hardware:
            raise HTTPException(status_code=404, detail="Hardware not found")
        
        return templates.TemplateResponse(
            "hardware_detail.html",
            {
                "request": request,
                "hardware": hardware,
                "current_user": current_user
            },
        )
    except Exception as e:
        logger.error(f"Error loading hardware detail: {e}")
        raise HTTPException(status_code=500, detail="Failed to load hardware details")


@router.get("/hardware/export/excel")
async def export_hardware_excel(
    db: Session = Depends(get_session),
    current_user = Depends(get_current_user),
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
            search=search,
            status=status,
            model=model,
            center=center
        )
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hardware_inventory_{timestamp}.xlsx"
        
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting hardware to Excel: {e}")
        raise HTTPException(status_code=500, detail="Failed to export data")


@router.get("/hardware-import", response_class=HTMLResponse)
async def bulk_import_form(request: Request, current_user = Depends(require_admin)):
    return templates.TemplateResponse("bulk_import.html", {"request": request})


@router.post("/hardware-import")
async def bulk_import(
    request: Request,
    db: Session = Depends(get_session),
    current_user = Depends(require_admin),
    file: UploadFile = File(...),
):
    try:
        hardware_service = HardwareService(db)

        filename = file.filename.lower()
        if not (filename.endswith('.csv') or filename.endswith('.xlsx') or filename.endswith('.xls')):
            raise HTTPException(status_code=400, detail="File must be a CSV or Excel file (.csv, .xlsx, .xls)")
        
        contents = await file.read()
        
        results = hardware_service.import_hardware_from_file(contents, filename, current_user)
        
        return templates.TemplateResponse(
            "bulk_import_results.html",
            {"request": request, "results": results}
        )
        
    except ValueError as e:
        logger.error(f"Invalid file format: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error importing file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import file: {str(e)}")


@router.get("/hardware/{hardware_id}/qr")
async def generate_qr_code(hardware_id: int, db: Session = Depends(get_session), current_user = Depends(require_visitor)):
    """Generate QR code for hardware detail page"""
    try:
        hardware_service = HardwareService(db)
        img_buffer, filename = hardware_service.generate_qr_code(hardware_id)
        
        return Response(
            content=img_buffer.getvalue(),
            media_type="image/png",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except ValueError as e:
        logger.error(f"Error generating QR code: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate QR code")


@router.get("/hardware/{hardware_id}/label")
async def generate_label_csv(hardware_id: int, db: Session = Depends(get_session), current_user = Depends(require_visitor)):
    try:
        hardware_service = HardwareService(db)
        csv_string, filename = hardware_service.generate_label_csv(hardware_id)
        
        return Response(
            content=csv_string,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        logger.error(f"Error generating label CSV: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating label CSV: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate label CSV")


@router.post("/hardware/{hardware_id}/status")
async def quick_status_change(
    hardware_id: int, 
    db: Session = Depends(get_session),
    current_user = Depends(require_admin),
    status: StatusEnum = Form(...),
):
    """Quick status change for hardware"""
    try:
        hardware_service = HardwareService(db)
        hardware = hardware_service.change_hardware_status(hardware_id, status, current_user)
        
        return {"success": True, "message": f"Status changed to {status.value}"}
        
    except ValueError as e:
        logger.error(f"Error changing status: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error changing status: {e}")
        raise HTTPException(status_code=500, detail="Failed to change status")


@router.post("/hardware/{hardware_id}/cycle-status")
async def cycle_status(
    request: Request,
    hardware_id: int, 
    db: Session = Depends(get_session),
    current_user = Depends(require_admin),
):
    try:
        hardware_service = HardwareService(db)
        hardware, status_display = hardware_service.cycle_hardware_status(hardware_id, current_user)
        
        status_class = hardware.status.value.lower().replace('_', '-')
        
        html = f'''
        <span class="status-pill status-{status_class}" title="Status">
            <span class="status-badge status-{status_class}"></span>
            {status_display}
        </span>
        '''
        
        return Response(content=html, media_type="text/html")
        
    except ValueError as e:
        logger.error(f"Error cycling status: {e}")
        if "already completed" in str(e) or "cannot be cycled" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error cycling status: {e}")
        raise HTTPException(status_code=500, detail="Failed to cycle status")


@router.get("/admin/audit-logs", response_class=HTMLResponse)
async def audit_logs_view(request: Request, db: Session = Depends(get_session), current_user = Depends(require_admin)):
    try:
        audit_service = AuditService(db)

        stats = audit_service.get_log_statistics(30)
        if stats is None:
            stats = {
                'period_days': 30,
                'total_requests': 0,
                'error_count': 0,
                'error_rate': 0,
                'avg_response_time_ms': 0,
                'status_codes': {},
                'top_endpoints': []
            }

        recent_errors = audit_service.get_recent_errors(20)
        if recent_errors is None:
            recent_errors = []
        
        return templates.TemplateResponse(
            "admin_audit_logs.html",
            { "request": request, "stats": stats, "recent_errors": recent_errors }
        )

    except Exception as e:
        logger.error(f"Error loading audit logs: {e}")
        return templates.TemplateResponse(
            "admin_audit_logs.html",
            {
                "request": request,
                "stats": {
                    'period_days': 30,
                    'total_requests': 0,
                    'error_count': 0,
                    'error_rate': 0,
                    'avg_response_time_ms': 0,
                    'status_codes': {},
                    'top_endpoints': []
                },
                "recent_errors": [],
                "error_message": f"Error loading audit logs: {str(e)}"
            }
        )
