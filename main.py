from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from io import BytesIO
import openpyxl
from openpyxl.worksheet.table import Table, TableStyleInfo
import logging

from database import SessionLocal, engine
from models import Hardware, Base, StatusEnum, ModelEnum


# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from sqlalchemy import func

@app.get("/", response_class=HTMLResponse)
def read_table(request: Request, db: Session = Depends(get_db)):
    hw_list = db.query(Hardware).all()
    filters = {"status": ""}

    # Zähle Geräte pro Modell im Status 'LAGER'
    lager_counts = (
        db.query(Hardware.model, func.count(Hardware.id))
        .filter(Hardware.status == StatusEnum.LAGER)
        .group_by(Hardware.model)
        .all()
    )
    model_lager_counter = {model or "Unbekannt": count for model, count in lager_counts}

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "hardware_list": hw_list,
            "filters": filters,
            "model_lager_counter": model_lager_counter,
        }
    )

@app.get("/add", response_class=HTMLResponse)
def add_form(request: Request):
    return templates.TemplateResponse("add_form.html", {
        "request": request,
        "StatusEnum": StatusEnum,
        "ModelEnum": ModelEnum
    })

@app.post("/add", response_class=HTMLResponse)
def add_entry(
    request: Request,
    hostname: str = Form(...), mac: str = Form(...), ip: str = Form(...),
    ticket: str = Form(None), uuid: str = Form(None), zentrum: str = Form(None), seriennumber: str = Form(None),
    status: str = Form(...), enduser: str = Form(None), model: str = Form(...), admin: str = Form(None), comment: str = Form(None),
    db: Session = Depends(get_db),
):
    try:
        hw = Hardware(
            hostname=hostname,
            mac=mac,
            ip=ip,
            ticket=ticket,
            uuid=uuid,
            zentrum=zentrum,
            seriennumber=seriennumber,
            status=StatusEnum(status),  # Kein `.upper()` nötig bei korrektem HTML
            model=ModelEnum(model),
            enduser=enduser,
            admin=admin,
            comment=comment,
            timestamp=datetime.utcnow()
        )
        db.add(hw)
        db.commit()
    except ValueError:
        return templates.TemplateResponse("add_form.html", {
            "request": request,
            "error": f"Ungültiger Status oder Modellwert: {status}, {model}",
            "StatusEnum": StatusEnum,
            "ModelEnum": ModelEnum
        })
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse("add_form.html", {
            "request": request,
            "error": "Fehler: Ungültige Daten oder Duplikat",
            "StatusEnum": StatusEnum,
            "ModelEnum": ModelEnum
        })
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"DB-Fehler: {e}")
        raise HTTPException(status_code=500, detail="Datenbankfehler")

    return RedirectResponse(url="/", status_code=303)

@app.post("/update_status/{hw_id}", response_class=HTMLResponse)
def update_status(hw_id: int, db: Session = Depends(get_db)):
    try:
        hw = db.query(Hardware).filter(Hardware.id == hw_id).first()
        if not hw:
            raise HTTPException(status_code=404, detail="Hardware nicht gefunden")

        if hw.status == StatusEnum.LAGER:
            hw.status = StatusEnum.BETANKUNG
        elif hw.status == StatusEnum.BETANKUNG:
            hw.status = StatusEnum.VERSAND
        elif hw.status == StatusEnum.VERSAND:
            hw.status = StatusEnum.ABGESCHLOSSEN
        else:
            hw.status = StatusEnum.LAGER

        db.commit()

        return f"""
        <td id='status-{hw.id}'>
            <button 
                hx-post='/update_status/{hw.id}' 
                hx-target='#status-{hw.id}' 
                hx-swap='outerHTML' 
                class='status-button'
                style='padding: 4px 10px; background-color: #f0f8ff; border: 1px solid #ccc; cursor: pointer;'
                title='Status ändern'>
                {hw.status.value}
            </button>
        </td>
        """
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Fehler beim Statusupdate: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Statusupdate")

class HardwareCreate(BaseModel):
    id: int = None
    hostname: str = None
    mac: str = None
    ip: str = None
    ticket: str = None
    uuid: str = None
    zentrum: str = None
    seriennumber: str
    status: str = None
    enduser: str = None
    model: str = None
    admin: str = None
    comment: str = None
    timestamp: str = None

@app.post("/api/hardware")
def api_add_entry(data: HardwareCreate, db: Session = Depends(get_db)):
    try:
        hw = Hardware(**data.dict())
        db.add(hw)
        db.commit()
        return {"message": "Hardware erfolgreich hinzugefügt"}
    except IntegrityError:
        db.rollback()
        return {"error": "Duplikat-ID oder ungültige Daten"}
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Fehler beim Hinzufügen per API: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Hinzufügen")

@app.get("/api/hardware", response_class=JSONResponse)
def get_hardware(db: Session = Depends(get_db)):
    try:
        results = db.query(Hardware).all()
        response_data = []
        for hw in results:
            row_dict = {}
            for column in hw.__table__.columns:
                value = getattr(hw, column.name)
                if isinstance(value, Enum):
                    value = value.value
                elif isinstance(value, datetime):
                    value = value.isoformat()
                row_dict[column.name] = value
            response_data.append(row_dict)
        return JSONResponse(content=response_data)
    except SQLAlchemyError as e:
        logger.error(f"Fehler beim Abruf per API: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Abruf")

@app.get("/export")
def export_excel(db: Session = Depends(get_db)):
    try:
        data = db.query(Hardware).all()

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Hardware"

        headers = [
            "ID", "Hostname", "MAC", "IP", "Ticket", "UUID", "Zentrum",
            "Seriennumber", "Status", "Enduser", "Model", "Admin", "Comment", "Timestamp"
        ]
        ws.append(headers)

        for hw in data:
            ws.append([
                hw.id,
                hw.hostname,
                hw.mac,
                hw.ip,
                hw.ticket or "",
                hw.uuid or "",
                hw.zentrum or "",
                hw.seriennumber or "",
                hw.status.value if hw.status else "",
                hw.enduser or "",
                hw.model or "",
                hw.admin or "",
                hw.comment or "",
                hw.timestamp.strftime("%Y-%m-%d %H:%M:%S") if hw.timestamp else ""
            ])

        # Tabelle korrekt definieren – exakte Spaltenbreite (A bis O = 15 Spalten)
        max_row = ws.max_row
        table_ref = f"A1:N{max_row}"
        display_name = f"HardwareTabelle_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        table = Table(displayName=display_name, ref=table_ref)
        style = TableStyleInfo(
            name="TableStyleMedium9",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        table.tableStyleInfo = style
        ws.add_table(table)

        # Spaltenbreiten automatisch anpassen
        for col in ws.columns:
            max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
            ws.column_dimensions[col[0].column_letter].width = max_length + 2

        output = BytesIO()
        wb.save(output)
        output.seek(0)

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=hardware_export.xlsx"}
        )

    except Exception as e:
        logger.exception("Fehler beim Excel-Export")
        raise HTTPException(status_code=500, detail="Fehler beim Excel-Export")


@app.get("/edit/{hw_id}", response_class=HTMLResponse)
def edit_form(request: Request, hw_id: int, db: Session = Depends(get_db)):
    hw = db.query(Hardware).get(hw_id)
    if not hw:
        raise HTTPException(status_code=404, detail="Hardware nicht gefunden")
    return templates.TemplateResponse("edit_form.html", {
    "request": request,
    "hw": hw,
    "StatusEnum": StatusEnum,
    "ModelEnum": ModelEnum 
})

@app.post("/edit/{hw_id}")
def update_entry(
    hw_id: int,
    hostname: str = Form(...), mac: str = Form(...), ip: str = Form(...),
    ticket: str = Form(None), uuid: str = Form(None), zentrum: str = Form(None), seriennumber: str = Form(None),
    status: str = Form(...), enduser: str = Form(None), model: str = Form(None), admin: str = Form(None), comment: str = Form(None),
    db: Session = Depends(get_db),
):
    hw = db.query(Hardware).get(hw_id)
    if not hw:
        raise HTTPException(status_code=404, detail="Hardware nicht gefunden")

    try:
        hw.hostname = hostname
        hw.mac = mac
        hw.ip = ip
        hw.ticket = ticket
        hw.uuid = uuid
        hw.zentrum = zentrum
        hw.seriennumber = seriennumber
        hw.status = StatusEnum(status.upper())
        hw.enduser = enduser
        hw.model = model
        hw.admin = admin
        hw.comment = comment
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Fehler beim Update: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Update")

    return RedirectResponse(url="/", status_code=303)

@app.post("/delete/{hw_id}")
def delete_entry(hw_id: int, db: Session = Depends(get_db)):
    try:
        hw = db.query(Hardware).get(hw_id)
        if not hw:
            raise HTTPException(status_code=404, detail="Hardware nicht gefunden")
        db.delete(hw)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Fehler beim Löschen: {e}")
        raise HTTPException(status_code=500, detail="Fehler beim Löschen")

    return RedirectResponse("/", status_code=303)

@app.get("/status/{status_filter}", response_class=HTMLResponse)
def read_filtered_table(request: Request, status_filter: str, db: Session = Depends(get_db)):
    try:
        status_enum = StatusEnum(status_filter.upper())
        hw_list = db.query(Hardware).filter(Hardware.status == status_enum).all()
    except ValueError:
        raise HTTPException(status_code=400, detail="Ungültiger Statuswert")
    except SQLAlchemyError as e:
        logger.error(f"Fehler beim Filtern: {e}")
        raise HTTPException(status_code=500, detail="Datenbankfehler beim Filtern")

    return templates.TemplateResponse("index.html", {
        "request": request,
        "hardware_list": hw_list,
        "filters": {"status": status_filter},
        "title": f"Geräte mit Status: {status_enum.value}"
    })


from reportlab.lib.pagesizes import mm
from reportlab.pdfgen import canvas

from fastapi.responses import StreamingResponse
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from io import BytesIO
from fastapi import Depends, HTTPException

@app.get("/label/{hw_id}")
def generate_label(hw_id: int, db: Session = Depends(get_db)):
    hw = db.query(Hardware).get(hw_id)
    if not hw:
        raise HTTPException(status_code=404, detail="Gerät nicht gefunden")

    buffer = BytesIO()

    # Match CSS-style page size: 30mm height × 62mm width (landscape)
    width_mm = 62
    height_mm = 30

    page_width = width_mm * mm
    page_height = height_mm * mm

    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))

    # Text layout
    x = 3 * mm
    y = page_height - 6 * mm
    line_height = 5 * mm

    c.setFont("Helvetica", 8)
    c.drawString(x, y, f"Hostname: {hw.hostname}")
    y -= line_height
    c.drawString(x, y, f"MAC: {hw.mac}")
    y -= line_height
    c.drawString(x, y, f"Ticket: {hw.ticket or '—'}")
    y -= line_height
    c.drawString(x, y, f"User: {hw.enduser or '—'}")

    c.showPage()
    c.save()
    buffer.seek(0)

    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": f"inline; filename=label_{hw.hostname}.pdf"
    })

@app.get("/lager_uebersicht", response_class=HTMLResponse)
def lager_uebersicht(request: Request, db: Session = Depends(get_db)):
    try:
        results = (
            db.query(Hardware.model, Hardware.seriennumber)
            .filter(Hardware.status == StatusEnum.LAGER)
            .filter(Hardware.seriennumber.isnot(None))
            .order_by(Hardware.model, Hardware.seriennumber)
            .all()
        )

        alle_modelle = list(ModelEnum)  # Enum-Objekte

        lager_geraete = {m: [] for m in alle_modelle}
        for model, seriennumber in results:
            lager_geraete[model].append(seriennumber)

        max_anzahl = max(len(sns) for sns in lager_geraete.values()) if lager_geraete else 0

        for model in lager_geraete:
            diff = max_anzahl - len(lager_geraete[model])
            if diff > 0:
                lager_geraete[model].extend([None] * diff)

        return templates.TemplateResponse("lager_uebersicht.html", {
            "request": request,
            "lager_geraete": lager_geraete,
            "max_anzahl": max_anzahl,
        })

    except Exception as e:
        logger.error(f"Fehler beim Laden der Lagerübersicht: {e}")
        raise HTTPException(status_code=500, detail="Fehler bei Lagerübersicht")
