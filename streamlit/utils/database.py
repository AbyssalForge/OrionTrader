"""
Database connection utilities for Streamlit
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager


# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = int(os.getenv("POSTGRES_PORT")
DB_NAME = os.getenv("POSTGRES_DB")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")

# URL de connexion
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print(f"[INFO] Database URL: postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")


# ============================================================================
# ENGINE & SESSION
# ============================================================================

# Engine SQLAlchemy avec pool de connexions
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
    echo=False,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_db_session() -> Session:
    """
    Retourne une nouvelle session DB

    Returns:
        Session SQLAlchemy
    """
    return SessionLocal()


@contextmanager
def get_db_context():
    """
    Context manager pour utilisation avec 'with'

    Usage:
        with get_db_context() as db:
            results = db.query(Model).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_database_connection() -> bool:
    """
    Teste la connexion à la base de données

    Returns:
        True si connexion OK, False sinon
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        return False
