"""
Database connection pour la base de données d'authentification FastAPI
Séparée de la base de données principale (trading data)
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator


AUTH_DB_HOST = os.getenv("FASTAPI_DB_HOST", "postgres")
AUTH_DB_PORT = int(os.getenv("FASTAPI_DB_PORT", "5432"))
AUTH_DB_NAME = os.getenv("FASTAPI_DB_NAME", "fastapi")
AUTH_DB_USER = os.getenv("FASTAPI_DB_USER", "fastapi")
AUTH_DB_PASSWORD = os.getenv("FASTAPI_DB_PASSWORD", "fastapi")

AUTH_DATABASE_URL = f"postgresql://{AUTH_DB_USER}:{AUTH_DB_PASSWORD}@{AUTH_DB_HOST}:{AUTH_DB_PORT}/{AUTH_DB_NAME}"

print(f"[INFO] Auth Database URL: postgresql://{AUTH_DB_USER}@{AUTH_DB_HOST}:{AUTH_DB_PORT}/{AUTH_DB_NAME}")



auth_engine = create_engine(
    AUTH_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    echo=False,
)

AuthSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=auth_engine)



def get_auth_db() -> Generator[Session, None, None]:
    """
    Dependency pour récupérer une session de la base de données auth

    Usage:
        @app.get("/tokens")
        def get_tokens(db: Session = Depends(get_auth_db)):
            return db.query(APIToken).all()
    """
    db = AuthSessionLocal()
    try:
        yield db
    finally:
        db.close()



@contextmanager
def get_auth_db_context():
    """
    Context manager pour utilisation hors FastAPI

    Usage:
        with get_auth_db_context() as db:
            results = db.query(APIToken).all()
    """
    db = AuthSessionLocal()
    try:
        yield db
    finally:
        db.close()



def test_auth_connection() -> bool:
    """
    Teste la connexion à la base de données auth

    Returns:
        True si connexion OK, False sinon
    """
    try:
        with auth_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"[ERROR] Auth database connection failed: {e}")
        return False


def init_auth_tables():
    """
    Crée les tables d'authentification si elles n'existent pas
    """
    from app.models.api_token import Base
    Base.metadata.create_all(bind=auth_engine)
    print("[INFO] Auth tables created/verified")
