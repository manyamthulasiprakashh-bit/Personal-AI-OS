from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
database_url = settings.database_url
engine_kwargs = {}
if settings.environment.lower() == "test":
    database_url = "sqlite+pysqlite:////tmp/personal_ai_os_test.db"
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(database_url, future=True, echo=False, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    if settings.environment.lower() == "test":
        Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
