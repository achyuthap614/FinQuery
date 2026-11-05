"""Database connection and session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from src.utils.config import settings
from src.utils.logger import logger

# SQLite requires check_same_thread=False for multi-threaded FastAPI access
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
    """Create database tables if they do not exist."""
    from src.database import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")

def get_db():
    """Dependency for providing a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
