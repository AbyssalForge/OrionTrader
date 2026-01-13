"""
Configuration centralisée pour FastAPI
Gère les chemins, imports et settings
"""

import sys
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

# ============================================================================
# PATHS CONFIGURATION
# ============================================================================

# Obtenir les chemins du projet
APP_DIR = Path(__file__).parent
FASTAPI_DIR = APP_DIR.parent
PROJECT_ROOT = FASTAPI_DIR.parent
AIRFLOW_DIR = PROJECT_ROOT / "airflow"
CLIENTS_DIR = FASTAPI_DIR / "clients"

# Ajouter airflow et clients au PYTHONPATH
for path in [str(AIRFLOW_DIR), str(CLIENTS_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)
        print(f"[INFO] Added to PYTHONPATH: {path}")

# Vérifier que les dossiers existent
if not AIRFLOW_DIR.exists():
    print(f"[WARNING] Airflow directory not found: {AIRFLOW_DIR}")
if not CLIENTS_DIR.exists():
    print(f"[WARNING] Clients directory not found: {CLIENTS_DIR}")


# ============================================================================
# APPLICATION SETTINGS
# ============================================================================

class Settings(BaseSettings):
    """
    Settings de l'application
    Charges automatiquement depuis .env
    """

    # Application
    APP_NAME: str = "OrionTrader API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Vault
    VAULT_ADDR: str = "http://localhost:8200"
    VAULT_TOKEN: Optional[str] = "orion-root-token"
    USE_VAULT: bool = True

    # Database (fallback si Vault indisponible)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "orion_trader"
    POSTGRES_USER: str = "airflow"
    POSTGRES_PASSWORD: str = "airflow"

    # CORS
    CORS_ORIGINS: list = ["*"]

    # Pool de connexions
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

    class Config:
        env_file = str(PROJECT_ROOT / ".env")
        case_sensitive = True


# Instance globale des settings
settings = Settings()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_database_url(host: str, port: int, db: str, user: str, password: str) -> str:
    """
    Construit l'URL de connexion PostgreSQL

    Args:
        host: Nom d'hôte
        port: Port
        db: Nom de la base
        user: Utilisateur
        password: Mot de passe

    Returns:
        URL de connexion PostgreSQL
    """
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def is_docker() -> bool:
    """
    Détecte si l'application tourne dans Docker

    Returns:
        True si dans Docker, False sinon
    """
    return os.path.exists('/.dockerenv') or os.getenv('DOCKER_CONTAINER', False)
