"""
Services module - Business logic pour le pipeline ETL
Contient la logique métier appelée par les tasks Airflow
"""

from .bronze_service import (
    initialize_database,
    extract_mt5_data,
    extract_stooq_data,
    extract_eurostat_data
)

from .silver_service import (
    transform_features,
    apply_feature_engineering
)

from .gold_service import (
    load_features_to_db
)

from .validation_service import (
    validate_data_quality,
    send_discord_notification
)

__all__ = [
    # Bronze - Extract (→ .parquet staging)
    'initialize_database',
    'extract_mt5_data',
    'extract_stooq_data',
    'extract_eurostat_data',
    # Silver - Transform (.parquet → .parquet features)
    'transform_features',
    'apply_feature_engineering',
    # Gold - Load (.parquet → DB)
    'load_features_to_db',
    # Validation
    'validate_data_quality',
    'send_discord_notification'
]
