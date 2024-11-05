from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic import BaseModel, Field
from typing import Dict

DATABASE_URL = "postgresql+psycopg2://postgres:1111@localhost:5432/satu-amo"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class APICredentials(Base):
    __tablename__ = 'api_credentials'
    id = Column(Integer, primary_key=True, index=True)
    api_url_satu = Column(String)
    api_token_satu = Column(String)
    api_url_amo = Column(String)
    api_token_amo = Column(String)
    pipeline_id = Column(Integer)
    address_id = Column(Integer)
    delivry_type_id = Column(Integer)
    payment_id = Column(Integer)
    product_id = Column(Integer)

Base.metadata.create_all(bind=engine)

class APICredentialsResponse(BaseModel):
    id: int
    api_url_satu: str
    api_url_amo: str
    pipeline_id: int

    class Config:
        from_attributes = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
