"""
ETL Forex Pipeline v3.0 - Architecture 3 Tables Sources

Architecture:
- 3 tables sources (mt5_eurusd_m15, yahoo_finance_daily, documents_macro)
- Composites calculés à l'export CSV (pas stockés en BDD)

Avantages:
- Pas de duplication (données macro pas répétées)
- Respect fréquences natives (M15, Daily, Monthly/Annual)
- Parallélisation complète (3 pipelines indépendants)
- Composites calculés à la demande (plus flexible)
"""

from airflow.decorators import dag, task
from datetime import datetime, timedelta

from services.bdd_service import initialize_database

from services.bronze_service import (
    extract_mt5_data,
    extract_stooq_data,
    extract_eurostat_data
)

from services.silver_service import (
    transform_mt5_features,
    transform_yahoo_features,
    transform_documents_features
)

from services.gold_service import (
    load_mt5_to_db,
    load_yahoo_to_db,
    load_documents_to_db
)

from services.validation_service import (
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

@dag(
    dag_id='ETL_forex_pipeline_v3',
    default_args=default_args,
    description="Pipeline ETL EURUSD - Bronze/Silver/Gold Architecture",
    catchup=False,
    tags=['forex', 'etl', 'v3', '3-tables']
)
def etl_forex_v3():
    """
    Pipeline ETL v3.0 - Architecture 3 tables sources

    Bronze (Extraction) → Silver (Transformation) → Gold (Load)
    3 sources → 3 transformations → 3 loads

    Composites: Calculés à l'export CSV (pas en BDD)
    """
    # ===========================================================
    # INITIALISATION
    # ===========================================================

    @task
    def initialize():
        """Bronze/Init: Créer les tables en bdd"""
        return initialize_database()

    
    # ========================================================================
    # BRONZE LAYER - Extraction
    # ========================================================================

    @task
    def extract_mt5():
        """Bronze/Extract: MT5 → data/mt5/*.parquet"""
        # Gestion des dates (730 jours = 2 ans)
        now = datetime.now()
        start = now - timedelta(days=730)
        end = now

        return extract_mt5_data(start, end)

    @task
    def extract_yahoo():
        """Bronze/Extract: Yahoo Finance → data/api/*.parquet"""
        return extract_stooq_data()

    @task
    def extract_documents():
        """Bronze/Extract: Documents → data/documents/*.parquet"""
        return extract_eurostat_data()


    # ========================================================================
    # SILVER LAYER - Transformations séparées
    # ========================================================================

    @task
    def transform_mt5(mt5_parquet: str):
        """Silver/Transform: MT5 → data/processed/mt5_features.parquet"""
        return transform_mt5_features(mt5_parquet)

    @task
    def transform_yahoo(yahoo_parquets: dict):
        """Silver/Transform: Yahoo → data/processed/yahoo_features.parquet"""
        return transform_yahoo_features(yahoo_parquets)

    @task
    def transform_documents(documents_parquets: dict):
        """Silver/Transform: Documents → data/processed/documents_features.parquet"""
        return transform_documents_features(documents_parquets)


    # ========================================================================
    # GOLD LAYER - Load séparé 
    # ========================================================================

    @task
    def load_mt5(mt5_parquet: str):
        """Gold/Load: MT5 → table mt5_eurusd_m15"""
        pipeline_run_id = f"v3_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return load_mt5_to_db(mt5_parquet, pipeline_run_id)

    @task
    def load_yahoo(yahoo_parquet: str):
        """Gold/Load: Yahoo → table yahoo_finance_daily"""
        pipeline_run_id = f"v3_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return load_yahoo_to_db(yahoo_parquet, pipeline_run_id)

    @task
    def load_documents(documents_parquet: str):
        """Gold/Load: Documents → table documents_macro"""
        pipeline_run_id = f"v3_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return load_documents_to_db(documents_parquet, pipeline_run_id)


    # ========================================================================
    # VALIDATION & NOTIFICATION
    # ========================================================================

    @task
    def validate_pipeline(mt5_result: dict, yahoo_result: dict, docs_result: dict):
        """Validation: Vérifier qualité données dans les 3 tables"""
        print("[VALIDATE] ==================== VALIDATION ====================")

        # Consolider les résultats des 3 loads
        validation_result = validate_data_quality(
            mt5_result=mt5_result,
            yahoo_result=yahoo_result,
            docs_result=docs_result
        )

        print(f"[VALIDATE] Statut global: {validation_result.get('status')}")
        print(f"[VALIDATE] Tables OK: {validation_result.get('tables_ok', 0)}/3")
        print("[VALIDATE] ==================== FIN ====================")

        return validation_result

    @task
    def notify(validation_result: dict):
        """Notification: Envoyer résumé sur Discord"""
        print("[NOTIFY] ==================== NOTIFICATION ====================")

        notification_result = send_discord_notification(
            validation_result=validation_result,
            webhook_url=DISCORD_WEBHOOK
        )

        print(f"[NOTIFY] Discord notification: {notification_result.get('status')}")
        print("[NOTIFY] ==================== FIN ====================")

        return notification_result


    # ========================================================================
    # DÉFINITION DU WORKFLOW
    # ========================================================================

    # Init
    init = initialize()

    # Extraction (parallèle)
    mt5_raw = extract_mt5()
    yahoo_raw = extract_yahoo()
    docs_raw = extract_documents()

    # Transformation sources (parallèle)
    mt5_features = transform_mt5(mt5_raw)
    yahoo_features = transform_yahoo(yahoo_raw)
    docs_features = transform_documents(docs_raw)

    # Load (parallèle)
    mt5_loaded = load_mt5(mt5_features)
    yahoo_loaded = load_yahoo(yahoo_features)
    docs_loaded = load_documents(docs_features)

    # Validation (après tous les loads)
    validation = validate_pipeline(mt5_loaded, yahoo_loaded, docs_loaded)

    # Notification (après validation)
    notification = notify(validation)

    # Dependencies
    init >> [mt5_raw, yahoo_raw, docs_raw]

    mt5_raw >> mt5_features >> mt5_loaded
    yahoo_raw >> yahoo_features >> yahoo_loaded
    docs_raw >> docs_features >> docs_loaded

    # Validation après tous les loads
    [mt5_loaded, yahoo_loaded, docs_loaded] >> validation >> notification


# Instancier le DAG
dag_instance = etl_forex_v3()
