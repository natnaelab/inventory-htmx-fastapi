from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "mysql+pymysql://appuser:apppass@192.168.200.99:3306/geraete_db"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)  # pool_pre_ping for connection health

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()
