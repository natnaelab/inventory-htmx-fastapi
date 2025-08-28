from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel, text, Column, String, DateTime, Boolean


class StatusEnum(str, Enum):
    IN_STOCK = "IN_STOCK"
    RESERVED = "RESERVED"
    IMAGING = "IMAGING"
    SHIPPED = "SHIPPED"
    COMPLETED = "COMPLETED"


class ModelEnum(str, Enum):
    Notebook = "Notebook"
    MFF = "MFF"
    AllInOne = "AllInOne"
    Backpack = "Backpack"
    DockingStation = "DockingStation"
    Monitor = "Monitor"


class Hardware(SQLModel, table=True):
    __tablename__ = "hardware"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    hostname: str = Field(max_length=255)
    mac: Optional[str] = Field(default=None, max_length=255)
    ip: Optional[str] = Field(default=None, max_length=255)
    ticket: Optional[str] = Field(default=None, max_length=255)
    po_ticket: Optional[str] = Field(default=None, max_length=255)
    uuid: Optional[str] = Field(default=None, max_length=255)
    center: Optional[str] = Field(default=None, sa_column=Column("center", String(255)))
    serial_number: str = Field(sa_column=Column("serial_number", String(255)))
    model: ModelEnum
    status: StatusEnum
    enduser: Optional[str] = Field(default=None, max_length=255)
    admin: str = Field(max_length=255)
    comment: Optional[str] = Field(default=None, max_length=1000)
    missing: bool = Field(default=False, sa_column=Column("missing", Boolean, default=False))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column("created_at", DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column("updated_at", DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")),
    )
    shipped_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column("shipped_at", DateTime(timezone=True), nullable=True),
    )
