from sqlalchemy import Column, Integer, String, Enum, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

class StatusEnum(str, enum.Enum):
    LAGER = "LAGER"
    BETANKUNG = "BETANKUNG"
    VERSENDET = "VERSENDET"

class Hardware(Base):
    __tablename__ = "hardware"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String(255))
    mac = Column(String(255))
    ip = Column(String(255))
    ticket = Column(String(255))
    uuid = Column(String(255))
    zentrum = Column(String(255))
    seriennumber = Column(String(255))
    status = Column(Enum(StatusEnum))
    enduser = Column(String(255))
    admin = Column(String(255))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
