"""
Database connection utilities for Streamlit
Uses Vault for secure credential management
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Dict


# ============================================================================
# VAULT INTEGRATION
# ============================================================================

def get_database_credentials() -> Dict[str, str]:
    """
    Récupère les credentials PostgreSQL depuis Vault ou variables d'environnement

    Priorité:
    1. Vault (si VAULT_ADDR et VAULT_TOKEN sont définis)
    2. Variables d'environnement (fallback)

    Returns:
        Dict avec les credentials PostgreSQL
    """
    # Vérifier si Vault est configuré
    vault_addr = os.getenv('VAULT_ADDR')
    vault_token = os.getenv('VAULT_TOKEN')

    if vault_addr and vault_token:
        try:
            from utils.vault_helper import get_vault

            vault = get_vault()
            credentials = vault.get_secret("Database")

            print("[OK] Database credentials retrieved from Vault")

            return {
                "POSTGRES_HOST": credentials.get("POSTGRES_HOST"),
                "POSTGRES_PORT": str(credentials.get("POSTGRES_PORT")),
                "POSTGRES_DB": credentials.get("POSTGRES_DB"),
                "POSTGRES_USER": credentials.get("POSTGRES_USER"),
                "POSTGRES_PASSWORD": credentials.get("POSTGRES_PASSWORD"),
            }

        except Exception as e:
            print(f"[WARNING] Could not retrieve credentials from Vault: {e}")
            print("[INFO] Falling back to environment variables")

    # Fallback: utiliser les variables d'environnement
    return {
        "POSTGRES_HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "POSTGRES_PORT": os.getenv("POSTGRES_PORT", "5432"),
        "POSTGRES_DB": os.getenv("POSTGRES_DB", "postgres"),
        "POSTGRES_USER": os.getenv("POSTGRES_USER", "postgres"),
        "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
    }


# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Récupérer les credentials depuis Vault ou env vars
credentials = get_database_credentials()

DB_HOST = credentials["POSTGRES_HOST"]
DB_PORT = int(credentials["POSTGRES_PORT"])
DB_NAME = credentials["POSTGRES_DB"]
DB_USER = credentials["POSTGRES_USER"]
DB_PASSWORD = credentials["POSTGRES_PASSWORD"]

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
