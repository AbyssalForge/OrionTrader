"""
Schémas Pydantic pour l'authentification par API Token
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TokenCreate(BaseModel):
    """Schéma pour créer un nouveau token"""
    name: str = Field(..., min_length=1, max_length=100, description="Nom descriptif du token")
    description: Optional[str] = Field(None, max_length=255, description="Description optionnelle")
    scopes: str = Field(default="read,write", description="Permissions (read,write,admin)")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Streamlit Dashboard",
                "description": "Token pour le dashboard Streamlit",
                "scopes": "read,write"
            }
        }


class TokenResponse(BaseModel):
    """Schéma de réponse après création d'un token"""
    id: int
    name: str
    token: str
    is_active: bool
    created_at: datetime
    description: Optional[str]
    scopes: str

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Streamlit Dashboard",
                "token": "abcd1234efgh5678ijkl9012mnop3456qrst7890uvwx1234yzab5678cdef",
                "is_active": True,
                "created_at": "2026-01-22T00:00:00",
                "description": "Token pour le dashboard Streamlit",
                "scopes": "read,write"
            }
        }


class TokenInfo(BaseModel):
    """Informations sur un token (sans le token lui-même)"""
    id: int
    name: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    description: Optional[str]
    scopes: str

    class Config:
        from_attributes = True


class TokenList(BaseModel):
    """Liste de tokens"""
    tokens: list[TokenInfo]
    total: int


class TokenRevoke(BaseModel):
    """Réponse après révocation d'un token"""
    message: str
    token_id: int
    name: str

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Token révoqué avec succès",
                "token_id": 1,
                "name": "Streamlit Dashboard"
            }
        }
