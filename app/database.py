# app/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import get_settings

# Core/config.py üzerinden .env’den çekilen ayarlar
settings = get_settings()

# Engine tanımı (SQLite için check_same_thread)
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
)

# Oturum (session) fabrikası
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Tüm modeller bu Base’in altından türeyecek
Base = declarative_base()
