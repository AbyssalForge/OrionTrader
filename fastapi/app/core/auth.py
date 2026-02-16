"""
Système d'authentification par API Token

Supporte deux modes d'authentification:
1. Master Token: Token défini dans FASTAPI_MASTER_TOKEN (variables d'env)
   - Accès complet avec droits admin
   - Pas stocké en base de données

2. Database Tokens: Tokens stockés dans la base de données "fastapi"
   - Gérables via l'API /auth/tokens
   - Peuvent avoir différents scopes (read, write, admin)
"""

import os
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, Union

from app.core.auth_database import get_auth_db
from app.models.api_token import APIToken

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_master_token() -> str:
    """Récupère le Master Token depuis les variables d'environnement"""
    return os.getenv("FASTAPI_MASTER_TOKEN", "")


class MasterTokenInfo:
    """
    Classe pour représenter le Master Token (token .env)
    Compatible avec l'interface APIToken pour les vérifications de droits
    """
    def __init__(self):
        self.id = 0
        self.name = "Master Token (ENV)"
        self.token = get_master_token()
        self.is_active = True
        self.created_at = datetime.utcnow()
        self.last_used_at = None
        self.description = "Token principal défini dans les variables d'environnement"
        self.scopes = "read,write,admin"  # Master token a tous les droits

    def __repr__(self):
        return "<MasterToken(name='Master Token (ENV)', scopes='read,write,admin')>"


async def verify_api_token(
    api_key: Optional[str] = Security(api_key_header),
    db: Session = Depends(get_auth_db)
) -> Union[APIToken, MasterTokenInfo]:
    """
    Vérifie la validité du token d'API

    Vérifie d'abord si c'est le Master Token, sinon cherche en base.

    Args:
        api_key: Token fourni dans le header X-API-Key
        db: Session de base de données auth

    Returns:
        APIToken ou MasterTokenInfo: Objet token si valide

    Raises:
        HTTPException: 401 si token invalide ou manquant
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'API manquant. Ajoutez le header 'X-API-Key: your_token'",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    master_token = get_master_token()
    if master_token and api_key == master_token:
        return MasterTokenInfo()

    token = db.query(APIToken).filter(APIToken.token == api_key).first()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'API invalide",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not token.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'API révoqué. Contactez l'administrateur.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    token.last_used_at = datetime.utcnow()
    db.commit()

    return token


async def verify_admin_token(
    token: Union[APIToken, MasterTokenInfo] = Depends(verify_api_token)
) -> Union[APIToken, MasterTokenInfo]:
    """
    Vérifie que le token a les droits admin

    Args:
        token: Token vérifié

    Returns:
        APIToken ou MasterTokenInfo: Token si admin

    Raises:
        HTTPException: 403 si pas les droits admin
    """
    if "admin" not in token.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Droits administrateur requis pour cette action"
        )

    return token
