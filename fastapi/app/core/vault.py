"""
Vault integration pour récupérer les credentials de manière sécurisée
Utilise vault_helper.py existant
"""

import os
from typing import Dict, Optional
from app.config import settings
from app.clients.vault_helper import get_vault


def get_database_credentials() -> Dict[str, str]:
    """
    Récupère les credentials PostgreSQL depuis Vault ou variables d'environnement

    Priorité:
    1. Vault (si USE_VAULT=True et Vault accessible)
    2. Variables d'environnement (fallback)

    Returns:
        Dict avec les credentials PostgreSQL
    """
    # Si USE_VAULT est désactivé, utiliser directement les env vars
    if not settings.USE_VAULT:
        print("[INFO] Vault disabled, using environment variables")
        return _get_credentials_from_env()

    # Essayer de récupérer depuis Vault
    try:

        vault = get_vault()
        credentials = vault.get_secret("Database")

        print("[OK] Database credentials retrieved from Vault")

        return {
            "POSTGRES_HOST": credentials.get("POSTGRES_HOST", settings.POSTGRES_HOST),
            "POSTGRES_PORT": str(credentials.get("POSTGRES_PORT", settings.POSTGRES_PORT)),
            "POSTGRES_DB": credentials.get("POSTGRES_DB", settings.POSTGRES_DB),
            "POSTGRES_USER": credentials.get("POSTGRES_USER", settings.POSTGRES_USER),
            "POSTGRES_PASSWORD": credentials.get("POSTGRES_PASSWORD", settings.POSTGRES_PASSWORD),
        }

    except Exception as e:
        print(f"[WARNING] Could not retrieve credentials from Vault: {e}")
        print("[INFO] Falling back to environment variables")
        return _get_credentials_from_env()


def _get_credentials_from_env() -> Dict[str, str]:
    """
    Récupère les credentials depuis les variables d'environnement

    Returns:
        Dict avec les credentials PostgreSQL
    """
    return {
        "POSTGRES_HOST": settings.POSTGRES_HOST,
        "POSTGRES_PORT": str(settings.POSTGRES_PORT),
        "POSTGRES_DB": settings.POSTGRES_DB,
        "POSTGRES_USER": settings.POSTGRES_USER,
        "POSTGRES_PASSWORD": settings.POSTGRES_PASSWORD,
    }


def test_vault_connection() -> bool:
    """
    Teste la connexion à Vault

    Returns:
        True si Vault est accessible, False sinon
    """
    try:
        vault = get_vault()
        return True
    except Exception as e:
        print(f"[WARNING] Vault connection test failed: {e}")
        return False
