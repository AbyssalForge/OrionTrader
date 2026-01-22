"""
Routes d'authentification - Gestion des API Tokens
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.schemas.auth import TokenCreate, TokenResponse, TokenInfo, TokenList, TokenRevoke
from app.models.api_token import APIToken
from app.core.auth import verify_admin_token
from app.core.auth_database import get_auth_db

router = APIRouter()


@router.post("/tokens", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def create_api_token(
    token_data: TokenCreate,
    db: Session = Depends(get_auth_db),
    admin_token: APIToken = Depends(verify_admin_token)
):
    """
    🔑 Créer un nouveau token d'API

    **Droits requis:** Admin

    Crée un nouveau token d'authentification pour accéder à l'API.

    **Use case:**
    - Créer un token pour Streamlit
    - Créer un token pour un bot de trading
    - Créer un token pour un service externe
    """
    # Générer le token
    new_token = APIToken(
        name=token_data.name,
        token=APIToken.generate_token(),
        description=token_data.description,
        scopes=token_data.scopes,
        is_active=True
    )

    db.add(new_token)
    db.commit()
    db.refresh(new_token)

    return new_token


@router.get("/tokens", response_model=TokenList)
def list_api_tokens(
    db: Session = Depends(get_auth_db),
    admin_token: APIToken = Depends(verify_admin_token)
):
    """
    📋 Lister tous les tokens d'API

    **Droits requis:** Admin

    Retourne la liste de tous les tokens (actifs et révoqués).
    """
    tokens = db.query(APIToken).all()

    return TokenList(
        tokens=[TokenInfo.model_validate(t) for t in tokens],
        total=len(tokens)
    )


@router.get("/tokens/{token_id}", response_model=TokenInfo)
def get_api_token(
    token_id: int,
    db: Session = Depends(get_auth_db),
    admin_token: APIToken = Depends(verify_admin_token)
):
    """
    🔍 Récupérer les informations d'un token

    **Droits requis:** Admin
    """
    token = db.query(APIToken).filter(APIToken.id == token_id).first()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Token ID {token_id} non trouvé"
        )

    return TokenInfo.model_validate(token)


@router.delete("/tokens/{token_id}", response_model=TokenRevoke)
def revoke_api_token(
    token_id: int,
    db: Session = Depends(get_auth_db),
    admin_token: APIToken = Depends(verify_admin_token)
):
    """
    🚫 Révoquer un token d'API

    **Droits requis:** Admin

    Désactive un token existant (il ne pourra plus être utilisé).
    """
    token = db.query(APIToken).filter(APIToken.id == token_id).first()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Token ID {token_id} non trouvé"
        )

    token.is_active = False
    db.commit()

    return TokenRevoke(
        message="Token révoqué avec succès",
        token_id=token.id,
        name=token.name
    )


@router.post("/tokens/{token_id}/activate", response_model=TokenInfo)
def activate_api_token(
    token_id: int,
    db: Session = Depends(get_auth_db),
    admin_token: APIToken = Depends(verify_admin_token)
):
    """
    ✅ Réactiver un token révoqué

    **Droits requis:** Admin
    """
    token = db.query(APIToken).filter(APIToken.id == token_id).first()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Token ID {token_id} non trouvé"
        )

    token.is_active = True
    db.commit()
    db.refresh(token)

    return TokenInfo.model_validate(token)


@router.get("/verify")
def verify_token(
    current_token: APIToken = Depends(verify_admin_token)
):
    """
    🔐 Vérifier la validité d'un token

    Endpoint pour tester si votre token est valide.

    **Headers requis:**
    - X-API-Key: votre_token
    """
    return {
        "valid": True,
        "token_name": current_token.name,
        "scopes": current_token.scopes,
        "is_active": current_token.is_active
    }
