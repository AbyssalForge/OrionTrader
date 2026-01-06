"""
Pipeline ETL EURUSD - Architecture Bronze/Silver/Gold
Version 2.0 - Modular & Production-Ready

Architecture ETL classique séparée:
1. Extract (Bronze): Données sources → .parquet
2. Transform (Silver): .parquet → Merge + Features → .parquet transformé
3. Load (Gold): .parquet transformé → DB + ML datasets

Workflow complet:
- Bronze: Extract (.parquet staging)
- Silver: Transform (harmonisation + feature engineering)
- Gold: Load (DB) + ML datasets
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.sdk import task

# Import des services (business logic)
from services import (
    # Init
    initialize_database,
    # Bronze - Extract
    extract_mt5_data,
    extract_stooq_data,
    extract_eurostat_data,
    # Silver - Transform
    transform_features,
    # Gold - Load + ML
    load_features_to_db,
    create_ml_dataset,
    # Validation
    validate_data_quality,
    send_discord_notification
)

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1447910339155988564/ybAszOuZF9HpV2djOQb_NtNSI_lgRL1swgQhmgB6jsfj9G5OMEstRP_U4rxobcfbspwJ"

# DAG CONFIG
default_args = {
    'owner': 'orion',
    'email_on_failure': True,
    'email': 'admin@oriontrader.ai',
    'retries': 2,
    'retry_delay': timedelta(minutes=3)
}

with DAG(
    dag_id="ETL_forex_EUR_USD_v2",
    default_args=default_args,
    description="Pipeline ETL EURUSD - Bronze/Silver/Gold Architecture",
    catchup=False,
    tags=["forex", "etl", "orion", "v2"],
):

    # ===========================================================
    # INITIALISATION
    # ===========================================================

    @task
    def init_database():
        """Initialise la base de données (crée les tables si nécessaire)"""
        print("[INIT] ==================== INITIALISATION ====================")
        result = initialize_database()
        print("[INIT] ==================== FIN ====================")
        return result

    # ===========================================================
    # BRONZE - EXTRACT (Données sources → .parquet)
    # ===========================================================

    @task
    def extract_mt5(**context):
        """Bronze/Extract: MT5 → data/mt5/eurusd_mt5.parquet"""
        print("[BRONZE/EXTRACT] ==================== EXTRACTION MT5 ====================")

        # Gestion des dates (30 jours par défaut)
        now = datetime.now()
        start = context.get("data_interval_start") or (now - timedelta(days=30))
        end = context.get("data_interval_end") or now

        if start == end:
            start = now - timedelta(days=30)
            end = now

        parquet_path = extract_mt5_data(start, end)
        print("[BRONZE/EXTRACT] ==================== FIN ====================")
        return parquet_path

    @task
    def extract_stooq():
        """Bronze/Extract: Stooq → data/api/*.parquet"""
        print("[BRONZE/EXTRACT] ==================== EXTRACTION STOOQ ====================")
        parquet_paths = extract_stooq_data()
        print("[BRONZE/EXTRACT] ==================== FIN ====================")
        return parquet_paths

    @task
    def extract_eurostat():
        """Bronze/Extract: Eurostat → data/documents/*.parquet"""
        print("[BRONZE/EXTRACT] ==================== EXTRACTION EUROSTAT ====================")
        parquet_paths = extract_eurostat_data()
        print("[BRONZE/EXTRACT] ==================== FIN ====================")
        return parquet_paths

    # ===========================================================
    # SILVER - TRANSFORM (.parquet → Merge → Features → .parquet)
    # ===========================================================

    @task
    def transform(mt5_parquet: str, stooq_parquets: dict, eurostat_parquets: dict):
        """
        Silver/Transform:
        1. Charge .parquet Bronze
        2. Merge multi-horizon (resample)
        3. Feature engineering
        4. Sauvegarde → data/processed/eurusd_features.parquet
        """
        print("[SILVER/TRANSFORM] ==================== TRANSFORMATION ====================")
        features_parquet = transform_features(mt5_parquet, stooq_parquets, eurostat_parquets)
        print("[SILVER/TRANSFORM] ==================== FIN ====================")
        return features_parquet

    # ===========================================================
    # GOLD - LOAD (.parquet → DB) + ML DATASETS
    # ===========================================================

    @task
    def load_to_db(features_parquet: str):
        """Gold/Load: .parquet → features_eurusd_m15 (DB)"""
        print("[GOLD/LOAD] ==================== CHARGEMENT DB ====================")
        load_result = load_features_to_db(features_parquet)
        print("[GOLD/LOAD] ==================== FIN ====================")
        return load_result

    @task
    def create_ml_datasets(load_result: dict):
        """Gold/ML: Features → ML datasets (TODO)"""
        print("[GOLD/ML] ==================== ML DATASETS ====================")
        ml_result = create_ml_dataset(load_result)
        print("[GOLD/ML] ==================== FIN ====================")
        return ml_result

    # ===========================================================
    # VALIDATION & NOTIFICATION
    # ===========================================================

    @task
    def validate_pipeline(load_result: dict):
        """Validation complète du pipeline"""
        print("[VALIDATE] ==================== VALIDATION ====================")

        # Créer des résultats fictifs pour Bronze (pas de DB Bronze)
        bronze_mt5 = {"status": "success", "rows": 0}
        bronze_stooq = {"status": "success", "rows": 0}
        bronze_eurostat = {"status": "success", "rows": 0}

        result = validate_data_quality(bronze_mt5, bronze_stooq, bronze_eurostat, load_result)
        print("[VALIDATE] ==================== FIN ====================")
        return result

    @task
    def notify(validation_result: dict):
        """Notification Discord"""
        print("[NOTIFY] ==================== NOTIFICATION ====================")
        result = send_discord_notification(validation_result, DISCORD_WEBHOOK)
        print("[NOTIFY] ==================== FIN ====================")
        return result

    # ===========================================================
    # CHAÎNAGE DU PIPELINE
    # ===========================================================

    # Init
    init = init_database()

    # Bronze - Extract (en parallèle)
    extract_mt5_task = extract_mt5()
    extract_stooq_task = extract_stooq()
    extract_eurostat_task = extract_eurostat()

    # Silver - Transform
    silver = transform(extract_mt5_task, extract_stooq_task, extract_eurostat_task)

    # Gold - Load + ML
    gold_load = load_to_db(silver)
    gold_ml = create_ml_datasets(gold_load)

    # Validation & Notification
    validation = validate_pipeline(gold_load)
    notification = notify(validation)

    # Dependencies
    init >> [extract_mt5_task, extract_stooq_task, extract_eurostat_task]
    [extract_mt5_task, extract_stooq_task, extract_eurostat_task] >> silver
    silver >> gold_load >> gold_ml
    gold_load >> validation >> notification
