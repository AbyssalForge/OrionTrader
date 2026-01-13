"""
FastAPI dependencies
"""

from app.config import settings, Settings
from app.core.database import SessionLocal


def get_db():
    """
    Dependency pour récupérer une session de base de données

    Usage:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_settings() -> Settings:
    """
    Dependency pour récupérer les settings

    Usage:
        @app.get("/config")
        def get_config(settings: Settings = Depends(get_current_settings)):
            return {"environment": settings.ENVIRONMENT}
    """
    return settings
