"""
Core functionality - Database, Vault, Dependencies
"""

from .database import engine, SessionLocal
from .vault import get_database_credentials
from .dependencies import get_db, get_current_settings

__all__ = [
    "get_db",
    "engine",
    "SessionLocal",
    "get_database_credentials",
    "get_current_settings",
]
