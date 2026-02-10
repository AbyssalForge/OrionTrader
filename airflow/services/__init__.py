"""
Services module - Business logic pour le pipeline ETL
Contient la logique métier appelée par les tasks Airflow
"""

from .bdd_service import initialize_database

from .bronze_service import (
    extract_mt5_data,
    extract_yahoo_data,
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
    send_discord_notification
)

__all__ = [
    'initialize_database',
    'extract_mt5_data',
    'extract_yahoo_data',
    'extract_eurostat_data',
    'transform_mt5_features',
    'transform_yahoo_features',
    'transform_documents_features',
    'load_mt5_to_db',
    'load_yahoo_to_db',
    'load_documents_to_db',
    'validate_data_quality',
    'send_discord_notification'
]
