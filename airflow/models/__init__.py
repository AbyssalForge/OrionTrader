"""
Modèles de base de données pour OrionTrader
Architecture Bronze/Silver/Gold avec SQLAlchemy ORM
"""

from .database import (
    # Base
    Base,
    get_engine,
    get_session,
    create_all_tables,
    drop_all_tables,

    # Bronze Layer (Raw Data)
    RawMT5EURUSDM15,
    RawStooqDaily,
    RawEurostatMacro,
    RawEconomicEvents,

    # Silver Layer (Features)
    FeaturesEURUSDM15,

    # Gold Layer (ML Datasets)
    MLClassificationDataset,
    MLRegressionDataset,
    RLEnvironmentState,
)

__all__ = [
    'Base',
    'get_engine',
    'get_session',
    'create_all_tables',
    'drop_all_tables',
    'RawMT5EURUSDM15',
    'RawStooqDaily',
    'RawEurostatMacro',
    'RawEconomicEvents',
    'FeaturesEURUSDM15',
    'MLClassificationDataset',
    'MLRegressionDataset',
    'RLEnvironmentState',
]
