from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
from io import BytesIO
import openpyxl
from openpyxl.worksheet.table import Table, TableStyleInfo

from database import SessionLocal, engine
from models import Hardware, Base, StatusEnum

app = FastAPI()

# DB-Tabellen erstellen beim Startup
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

# Templates & Static Files konfigurieren
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# DB-Session Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- HTML ROUTES ---

@app.get("/", response_class=HTMLResponse)
def read_table(request: Request, db: Session = Depends(get_db)):
    hw_list = db.query(Hardware).all()
    filters = {"status": ""}
    return templates.TemplateResponse("index.html", {"request": request, "hardware_list": hw_list, "filters": filters})

@app.get("/add", response_class=HTMLResponse)
def add_form(request: Request):
    return templates.TemplateResponse("add_form.html", {"request": request})

@app.post("/add", response_class=HTMLResponse)
def add_entry(
    request: Request,
    hostname: str = Form(...),
    mac: str = Form(...),
    ip: str = Form(...),
    ticket: str = Form(...),
    uuid: str = Form(...),
    zentrum: str = Form(...),
    seriennumber: str = Form(...),
    status: str = Form(...),
    enduser: str = Form(...),
    admin: str = Form(...),
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
            status=StatusEnum(status.upper()),
            enduser=enduser,
            admin=admin,
            timestamp=datetime.utcnow(),
        )
    except ValueError:
        return templates.TemplateResponse("add_form.html", {"request": request, "error": f"Ungültiger Statuswert: {status}"})

    db.add(hw)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse("add_form.html", {"request": request, "error": "Fehler: Ungültige Daten oder Duplikat"})

    return RedirectResponse(url="/", status_code=303)

@app.post("/update_status/{hw_id}", response_class=HTMLResponse)
def update_status(hw_id: int, db: Session = Depends(get_db)):
    hw = db.query(Hardware).filter(Hardware.id == hw_id).first()
    if not hw:
        raise HTTPException(status_code=404, detail="Hardware nicht gefunden")

    # Status rotieren
    if hw.status == StatusEnum.LAGER:
        hw.status = StatusEnum.BETANKUNG
    elif hw.status == StatusEnum.BETANKUNG:
        hw.status = StatusEnum.VERSENDET
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

# --- API ROUTES ---

class HardwareCreate(BaseModel):
    id: int
    hostname: str
    mac: str
    ip: str
    ticket: str
    uuid: str
    zentrum: str
    seriennumber: str
    status: str
    enduser: str
    admin: str
    timestamp: str

@app.post("/api/hardware")
def api_add_entry(data: HardwareCreate, db: Session = Depends(get_db)):
    hw = Hardware(**data.dict())
    db.add(hw)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"error": "Duplikat-ID oder ungültige Daten"}
    return {"message": "Hardware erfolgreich hinzugefügt"}

@app.get("/api/hardware", response_class=JSONResponse)
def get_hardware(db: Session = Depends(get_db)):
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

# --- Excel Export ---

@app.get("/export")
def export_excel(db: Session = Depends(get_db)):
    data = db.query(Hardware).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Hardware"

    headers = [
        "ID", "Hostname", "MAC", "IP", "Ticket", "UUID", "Zentrum",
        "SerienNumber", "Status", "Enduser", "Admin", "Timestamp"
    ]
    ws.append(headers)

    for hw in data:
        ws.append([
            hw.id, hw.hostname, hw.mac, hw.ip, hw.ticket, hw.uuid,
            hw.zentrum, hw.seriennumber,
            hw.status.value if hw.status else "",
            hw.enduser, hw.admin,
            hw.timestamp.strftime("%Y-%m-%d %H:%M:%S") if hw.timestamp else ""
        ])

    table_ref = f"A1:L{ws.max_row}"
    tab = Table(displayName="HardwareTabelle", ref=table_ref)

    style = TableStyleInfo(
        name="TableStyleMedium9",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False
    )
    tab.tableStyleInfo = style
    ws.add_table(tab)

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

# --- Edit Hardware ---

from models import StatusEnum  # falls noch nicht importiert

@app.get("/edit/{hw_id}", response_class=HTMLResponse)
def edit_form(request: Request, hw_id: int, db: Session = Depends(get_db)):
    hw = db.query(Hardware).get(hw_id)
    if not hw:
        raise HTTPException(status_code=404, detail="Hardware nicht gefunden")
    return templates.TemplateResponse("edit_form.html", {
        "request": request,
        "hw": hw,
        "StatusEnum": StatusEnum  # Hier StatusEnum mitgeben
    })

@app.post("/edit/{hw_id}")
def update_entry(
    hw_id: int,
    hostname: str = Form(...),
    mac: str = Form(...),
    ip: str = Form(...),
    ticket: str = Form(...),
    uuid: str = Form(...),
    zentrum: str = Form(...),
    seriennumber: str = Form(...),
    status: str = Form(...),
    enduser: str = Form(...),
    admin: str = Form(...),
    db: Session = Depends(get_db),
):
    hw = db.query(Hardware).get(hw_id)
    if not hw:
        raise HTTPException(status_code=404, detail="Hardware nicht gefunden")

    hw.hostname = hostname
    hw.mac = mac
    hw.ip = ip
    hw.ticket = ticket
    hw.uuid = uuid
    hw.zentrum = zentrum
    hw.seriennumber = seriennumber

    try:
        hw.status = StatusEnum(status.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="Ungültiger Statuswert")

    hw.enduser = enduser
    hw.admin = admin

    db.commit()
    return RedirectResponse(url="/", status_code=303)

# --- Delete Hardware ---

@app.post("/delete/{hw_id}")
def delete_entry(hw_id: int, db: Session = Depends(get_db)):
    hw = db.query(Hardware).get(hw_id)
    if not hw:
        raise HTTPException(status_code=404, detail="Hardware nicht gefunden")
    db.delete(hw)
    db.commit()
    return RedirectResponse("/", status_code=303)


@app.get("/status/{status_filter}", response_class=HTMLResponse)
def read_filtered_table(request: Request, status_filter: str, db: Session = Depends(get_db)):
    # StatusEnum erwartet Großbuchstaben (so wie du es oben nutzt)
    try:
        status_enum = StatusEnum(status_filter.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail="Ungültiger Statuswert")

    hw_list = db.query(Hardware).filter(Hardware.status == status_enum).all()
    filters = {"status": status_filter}

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "hardware_list": hw_list,
            "filters": filters,
            "title": f"Geräte mit Status: {status_enum.value}"
        },
    )