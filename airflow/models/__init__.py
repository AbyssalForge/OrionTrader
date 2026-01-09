"""
Modèles de base de données pour OrionTrader
Pipeline ETL v2 - Uniquement la table features (Gold Layer)
"""

# Base et fonctions utilitaires
from .base import (
    Base,
    get_engine,
    get_session,
    create_all_tables,
    drop_all_tables,
)

# Gold Layer - Features finales
from .FeaturesEURUSDM15 import FeaturesEURUSDM15

__all__ = [
    # Base
    'Base',
    'get_engine',
    'get_session',
    'create_all_tables',
    'drop_all_tables',

    # Gold Layer - Table unique du pipeline v2
    'FeaturesEURUSDM15',
]
