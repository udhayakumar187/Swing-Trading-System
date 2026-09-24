from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import get_settings
from app.models.base import Base


def get_engine():
    settings = get_settings()
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
        pool_pre_ping=True,
        echo=settings.LOG_LEVEL == "DEBUG",
    )
    return engine


def create_tables():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def drop_tables():
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)


def get_session_factory():
    engine = get_engine()
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


SessionLocal = get_session_factory()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()