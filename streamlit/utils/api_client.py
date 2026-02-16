"""
API client utilities for Streamlit
Connects to FastAPI backend
"""

import os
import requests
from typing import Dict, Any, Optional



FASTAPI_URL = os.getenv("FASTAPI_URL", "http://fastapi:8000")



def get_health_status() -> Dict[str, Any]:
    """
    Récupère le statut de santé de l'API

    Returns:
        Dict avec status, database, tables counts
    """
    try:
        response = requests.get(f"{FASTAPI_URL}/health", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Health check failed: {e}")
        return {"status": "error", "message": str(e)}


def get_market_snapshot() -> Dict[str, Any]:
    """
    Récupère le dernier market snapshot

    Returns:
        Dict avec tous les champs du snapshot
    """
    try:
        response = requests.get(f"{FASTAPI_URL}/market/latest", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Get market snapshot failed: {e}")
        return {}


def get_market_history(limit: int = 100) -> list:
    """
    Récupère l'historique des snapshots

    Args:
        limit: Nombre de snapshots à récupérer

    Returns:
        Liste de snapshots
    """
    try:
        response = requests.get(
            f"{FASTAPI_URL}/market/history",
            params={"limit": limit},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Get market history failed: {e}")
        return []


def get_signals(confidence_threshold: float = 0.6, limit: int = 50) -> list:
    """
    Récupère les signaux de trading avec haute confiance

    Args:
        confidence_threshold: Seuil minimum de confiance
        limit: Nombre maximum de signaux

    Returns:
        Liste de signaux
    """
    try:
        response = requests.get(
            f"{FASTAPI_URL}/signals/high-confidence",
            params={
                "min_confidence": confidence_threshold,
                "limit": limit
            },
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Get signals failed: {e}")
        return []
