from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://appuser:apppass@localhost:3306/geraete_db")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)  # pool_pre_ping for connection health

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()
