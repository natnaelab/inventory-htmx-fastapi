from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.dependencies.auth import get_current_user
from app.models.hardware import ModelEnum, StatusEnum
from app.services.auth import UserRole
from app.services.hardware import HardwareService

router = APIRouter()


class HardwareImportItem(BaseModel):
    serial_number: str = Field(..., description="Unique serial number of the hardware")
    hostname: str
    model: str
    status: str
    ip: Optional[str] = None
    mac: Optional[str] = None
    uuid: Optional[str] = None
    center: Optional[str] = None
    enduser: Optional[str] = None
    ticket: Optional[str] = None
    po_ticket: Optional[str] = None
    comment: Optional[str] = None
    missing: Optional[bool] = False


class HardwareImportPayload(BaseModel):
    items: List[HardwareImportItem]


class HardwareImportError(BaseModel):
    serial_number: Optional[str] = None
    error: str


class HardwareImportResult(BaseModel):
    created: int
    updated: int
    failed: int
    errors: List[HardwareImportError] = []


def _normalize_legacy_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    if "SerialNumber" not in raw:
        raise ValueError("SerialNumber is required")

    model = raw.get("Model") or "Notebook"
    status = raw.get("Status") or "IN_STOCK"

    return {
        "serial_number": str(raw.get("SerialNumber", "")).strip(),
        "hostname": str(raw.get("Hostname", "")).strip() or f"device-{raw['SerialNumber']}",
        "model": str(model).strip(),
        "status": str(status).strip(),
        "ip": raw.get("ActiveIP"),
        "mac": raw.get("LANMAC"),
        "uuid": raw.get("UUID"),
        "center": raw.get("Center"),
        "enduser": raw.get("LoggedOnUser"),
        "ticket": raw.get("TicketNumber"),
        "po_ticket": raw.get("POTicket"),
        "comment": raw.get("Comment") or raw.get("Heartbeat"),
        "missing": False,
    }


def _coerce_payload(payload: Union[Dict[str, Any], HardwareImportPayload]) -> HardwareImportPayload:
    if isinstance(payload, HardwareImportPayload):
        return payload

    if isinstance(payload, dict) and "SerialNumber" in payload:
        normalized = _normalize_legacy_item(payload)
        return HardwareImportPayload(items=[HardwareImportItem(**normalized)])

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload format")


@router.post("/hardware/import", response_model=HardwareImportResult)
def import_hardware(
    payload: Union[HardwareImportPayload, Dict[str, Any]],
    request: Request,
    db: Session = Depends(get_session),
):
    current_user = get_current_user(request)
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    if current_user["role"] != UserRole.ADMINISTRATOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator privileges required")

    service = HardwareService(db)
    coerced_payload = _coerce_payload(payload)

    created = 0
    updated = 0
    errors: List[HardwareImportError] = []

    for item in coerced_payload.items:
        try:
            hardware_data = {
                "hostname": item.hostname.strip(),
                "serial_number": item.serial_number.strip(),
                "model": ModelEnum(item.model),
                "status": StatusEnum(item.status),
                "ip": item.ip.strip() if item.ip else None,
                "mac": item.mac.strip() if item.mac else None,
                "uuid": item.uuid.strip() if item.uuid else None,
                "center": item.center.strip() if item.center else None,
                "enduser": item.enduser.strip() if item.enduser else None,
                "ticket": item.ticket.strip() if item.ticket else None,
                "po_ticket": item.po_ticket.strip() if item.po_ticket else None,
                "comment": item.comment.strip() if item.comment else None,
                "missing": bool(item.missing),
            }

            action, _ = service.upsert_hardware_by_serial(hardware_data, current_user)
            if action == "created":
                created += 1
            else:
                updated += 1

        except (ValueError, KeyError) as exc:
            errors.append(HardwareImportError(serial_number=item.serial_number, error=str(exc)))
        except Exception as exc:
            errors.append(
                HardwareImportError(
                    serial_number=item.serial_number,
                    error="Unexpected error: {}".format(str(exc)),
                )
            )

    failed = len(errors)

    return HardwareImportResult(created=created, updated=updated, failed=failed, errors=errors)
