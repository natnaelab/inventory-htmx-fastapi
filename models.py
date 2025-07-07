from sqlalchemy import Column, Integer, String, Enum, DateTime, func
from database import Base
import enum

class StatusEnum(str, enum.Enum):
    LAGER = "LAGER"
    RESERVIERT = "RESERVIERT"
    BETANKUNG = "BETANKUNG"
    VERSENDET = "VERSENDET"
    FEHLER = "FEHLER"
    ABGESCHLOSSEN = "ABGESCHLOSSEN"

class ModelEnum(str, enum.Enum):
    NOTEBOOKS = "Notebook"
    MFF = "MFF"
    ALL_IN_ONE = "All-In-One"
    SCANNER = "Scanner"
    DRUCKER = "Drucker"
    MULTIFUNKTIONSDRUCKER = "Multifunktionsdrucker"
    ZUFUHRFACH = "Zufuhrfach"
    IPHONE = "iPhone"

class Hardware(Base):
    __tablename__ = "hardware"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String(255))
    mac = Column(String(255), nullable=True)
    ip = Column(String(255), nullable=True)
    ticket = Column(String(255), nullable=True)
    uuid = Column(String(255), nullable=True)
    zentrum = Column(String(255), nullable=True)
    seriennumber = Column(String(255))
    model = Column(Enum(ModelEnum))
    status = Column(Enum(StatusEnum))

    enduser = Column(String(255), nullable=True)
    admin = Column(String(255))
    comment = Column(String(1000), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

