"""
Services module - Business logic pour le pipeline ETL
Contient la logique métier appelée par les tasks Airflow
"""

from .bdd_service import initialize_database

from .bronze_service import (
    extract_yahoo_data,  # Yahoo Finance: 15m + Daily (remplace MT5)
    extract_eurostat_data
)

from .silver_service import (
    transform_mt5_features,
    transform_yahoo_features,
    transform_documents_features
)

from .gold_service import (
    load_mt5_to_db,
    load_yahoo_to_db,
    load_documents_to_db
)

from .validation_service import (
    validate_data_quality,
    send_discord_notification,
    send_wikipedia_notification
)

__all__ = [
    # Bronze - Extract (→ .parquet staging)
    'initialize_database',
    'extract_yahoo_data',  # Yahoo Finance: 15m + Daily (unifié)
    'extract_eurostat_data',
    # Silver - Transform (.parquet → .parquet features)
    'transform_mt5_features',  # Note: traite maintenant EUR/USD 15m Yahoo
    'transform_yahoo_features',
    'transform_documents_features',
    # Gold - Load (.parquet → DB)
    'load_mt5_to_db',  # Note: charge maintenant EUR/USD 15m Yahoo
    'load_yahoo_to_db',
    'load_documents_to_db',
    # Validation
    'validate_data_quality',
    'send_discord_notification',
    'send_wikipedia_notification'
]
