"""
Database connection utilities for Streamlit
Uses Vault for secure credential management
"""

import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Dict



def get_database_credentials() -> Dict[str, str]:
    """
    Récupère les credentials PostgreSQL depuis Vault ou variables d'environnement

    Priorité:
    1. Vault (si VAULT_ADDR et VAULT_TOKEN sont définis)
    2. Variables d'environnement (fallback)

    Returns:
        Dict avec les credentials PostgreSQL
    """
    vault_addr = os.getenv('VAULT_ADDR')
    vault_token = os.getenv('VAULT_TOKEN')

    if vault_addr and vault_token:
        try:
            from utils.vault_helper import get_vault

            vault = get_vault()
            credentials = vault.get_secret("Database")

            print("[OK] Database credentials retrieved from Vault")

            # POSTGRES_HOST env var a priorité sur Vault
            # (dans Docker, wg-easy est le hostname réseau, pas 10.8.0.1)
            return {
                "POSTGRES_HOST": os.getenv("POSTGRES_HOST") or credentials.get("POSTGRES_HOST"),
                "POSTGRES_PORT": os.getenv("POSTGRES_PORT") or str(credentials.get("POSTGRES_PORT")),
                "POSTGRES_DB": credentials.get("POSTGRES_DB"),
                "POSTGRES_USER": credentials.get("POSTGRES_USER"),
                "POSTGRES_PASSWORD": credentials.get("POSTGRES_PASSWORD"),
            }

        except Exception as e:
            print(f"[WARNING] Could not retrieve credentials from Vault: {e}")
            print("[INFO] Falling back to environment variables")

    return {
        "POSTGRES_HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "POSTGRES_PORT": os.getenv("POSTGRES_PORT", "5432"),
        "POSTGRES_DB": os.getenv("POSTGRES_DB", "postgres"),
        "POSTGRES_USER": os.getenv("POSTGRES_USER", "postgres"),
        "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
    }



_engine = None


def _get_engine():
    """Crée l'engine SQLAlchemy à la demande (lazy) pour éviter les échecs au démarrage."""
    global _engine
    if _engine is None:
        credentials = get_database_credentials()
        db_host = credentials["POSTGRES_HOST"]
        db_port = int(credentials["POSTGRES_PORT"])
        db_name = credentials["POSTGRES_DB"]
        db_user = credentials["POSTGRES_USER"]
        db_password = credentials["POSTGRES_PASSWORD"]

        database_url = (
            f"postgresql://{quote_plus(db_user)}:{quote_plus(db_password)}"
            f"@{db_host}:{db_port}/{db_name}"
        )
        print(f"[INFO] Connecting to: postgresql://{db_user}@{db_host}:{db_port}/{db_name}")

        _engine = create_engine(
            database_url,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=3600,
            echo=False,
        )
    return _engine


def get_db_session() -> Session:
    return sessionmaker(autocommit=False, autoflush=False, bind=_get_engine())()


@contextmanager
def get_db_context():
    db = sessionmaker(autocommit=False, autoflush=False, bind=_get_engine())()
    try:
        yield db
    finally:
        db.close()


def get_db_connection():
    """Retourne une connexion SQLAlchemy (pour pd.read_sql). Lève une exception si échec."""
    engine = _get_engine()
    return engine.connect()


def test_database_connection() -> bool:
    try:
        with _get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        return False
