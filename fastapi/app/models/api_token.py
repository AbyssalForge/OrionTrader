"""
Modèle SQLAlchemy pour les tokens d'API
"""

from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import secrets

Base = declarative_base()


class APIToken(Base):
    """Table des tokens d'API pour l'authentification"""

    __tablename__ = "api_tokens"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="Nom descriptif du token (ex: 'Streamlit Dashboard', 'Production Bot')")
    token = Column(String(64), unique=True, index=True, nullable=False, comment="Token d'authentification (64 caractères)")
    is_active = Column(Boolean, default=True, nullable=False, comment="Token actif ou révoqué")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True, comment="Dernière utilisation du token")
    description = Column(String(255), nullable=True, comment="Description optionnelle")
    scopes = Column(String(255), default="read,write", nullable=False, comment="Permissions (read,write,admin)")

    def __repr__(self):
        return f"<APIToken(name='{self.name}', active={self.is_active})>"

    @staticmethod
    def generate_token():
        """Génère un token aléatoire sécurisé de 64 caractères"""
        return secrets.token_urlsafe(48)[:64]
