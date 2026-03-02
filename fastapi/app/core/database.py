"""
Database connection avec pool de connexions
Utilise Vault pour récupérer les credentials
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

from app.config import settings, get_database_url
from app.core.vault import get_database_credentials

DB_HOST = os.getenv("FASTAPI_DB_HOST", "postgres")
DB_PORT = int(os.getenv("FASTAPI_DB_PORT", "5432"))
DB_NAME = os.getenv("FASTAPI_DB_DATA_NAME", "trading_data")
DB_USER = os.getenv("FASTAPI_DB_USER", "fastapi")
DB_PASSWORD = os.getenv("FASTAPI_DB_PASSWORD", "fastapi")

DATABASE_URL = get_database_url(
    host=DB_HOST,
    port=DB_PORT,
    db=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)

print(f"[INFO] Database URL: postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")



engine = create_engine(
    DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    echo=False,  # Mettre True pour debug SQL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



@contextmanager
def get_db_context():
    """
    Context manager pour utilisation hors FastAPI

    Usage:
        with get_db_context() as db:
            results = db.query(Model).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



def test_connection() -> bool:
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


def get_table_counts() -> dict:
    """
    Récupère le nombre de lignes dans chaque table

    Returns:
        Dict avec le nombre de lignes par table
    """
    from models import MT5EURUSDM15, YahooFinanceDaily, DocumentsMacro, MarketSnapshotM15

    counts = {}

    try:
        with get_db_context() as db:
            counts["mt5_eurusd_m15"] = db.query(MT5EURUSDM15).count()
            counts["yahoo_finance_daily"] = db.query(YahooFinanceDaily).count()
            counts["documents_macro"] = db.query(DocumentsMacro).count()
            counts["market_snapshot_m15"] = db.query(MarketSnapshotM15).count()
    except Exception as e:
        print(f"[ERROR] Could not count tables: {e}")
        counts = {}

    return counts
