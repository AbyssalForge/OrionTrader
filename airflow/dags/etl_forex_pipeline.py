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

from airflow.sdk import dag, task
from datetime import datetime, timedelta

from services.bdd_service import initialize_database

from services.bronze_service import (
    extract_mt5_data,
    extract_yahoo_data,
    extract_eurostat_data
)

from services.silver_service import (
    transform_mt5_features,
    transform_yahoo_features,
    transform_documents_features,
    transform_market_snapshot
)

from services.gold_service import (
    load_mt5_to_db,
    load_yahoo_to_db,
    load_documents_to_db,
    load_market_snapshot_to_db
)

from services.validation_service import (
    validate_data_quality,
    send_discord_notification
)

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1447910339155988564/ybAszOuZF9HpV2djOQb_NtNSI_lgRL1swgQhmgB6jsfj9G5OMEstRP_U4rxobcfbspwJ"

# Dates par défaut (peuvent être écrasées lors du lancement manuel)
# Ces valeurs seront utilisées si aucun paramètre n'est fourni
DEFAULT_DATE_NOW = datetime.now()

# MT5 et Yahoo: J-2 → J-1 (données complètes de la veille)
DEFAULT_DATE_START = DEFAULT_DATE_NOW - timedelta(days=2)
DEFAULT_DATE_END = DEFAULT_DATE_NOW - timedelta(days=1)

# Documents: 5 ans avant (données macro mensuelles/trimestrielles)
DEFAULT_DOCUMENT_START = DEFAULT_DATE_NOW - timedelta(days=1825)  # ~5 ans

# DAG CONFIG
default_args = {
    'owner': 'orion',
    'email_on_failure': True,
    'email': 'admin@oriontrader.ai',
    'retries': 2,
    'retry_delay': timedelta(minutes=3)
}

@dag(
    dag_id='ETL_forex_pipeline',
    default_args=default_args,
    description="Pipeline ETL EURUSD - Bronze/Silver/Gold Architecture",
    schedule='0 18 * * *',  # Tous les jours à 18h00 UTC (19h CET / 20h CEST)
    catchup=False,
    tags=['forex', 'etl'],
    params={
        # MT5 dates (J-2 → J-1)
        'start_mt5': DEFAULT_DATE_START.strftime('%Y-%m-%d'),
        'end_mt5': DEFAULT_DATE_END.strftime('%Y-%m-%d'),
        # Yahoo dates (J-2 → J-1)
        'start_yahoo': DEFAULT_DATE_START.strftime('%Y-%m-%d'),
        'end_yahoo': DEFAULT_DATE_END.strftime('%Y-%m-%d'),
        # Document dates (5 ans avant → aujourd'hui)
        'start_document': DEFAULT_DOCUMENT_START.strftime('%Y-%m-%d'),
    }
)
def etl_forex():
    """
    Pipeline ETL

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
    def extract_mt5(**context):
        """Bronze/Extract: MT5 → data/mt5/*.parquet"""
        # Récupérer les dates depuis les paramètres du DAG run
        params = context.get('params', {})
        start_str = params.get('start_mt5', DEFAULT_DATE_START.strftime('%Y-%m-%d'))
        end_str = params.get('end_mt5', DEFAULT_DATE_END.strftime('%Y-%m-%d'))

        start = datetime.strptime(start_str, '%Y-%m-%d')
        end = datetime.strptime(end_str, '%Y-%m-%d')

        print(f"[MT5] Extraction avec dates: start={start.date()}, end={end.date()}")
        return extract_mt5_data(start, end)

    @task
    def extract_yahoo(**context):
        """Bronze/Extract: Yahoo Finance → data/api/*.parquet"""
        # Récupérer les dates depuis les paramètres du DAG run
        params = context.get('params', {})
        start_str = params.get('start_yahoo', DEFAULT_DATE_START.strftime('%Y-%m-%d'))
        end_str = params.get('end_yahoo', DEFAULT_DATE_END.strftime('%Y-%m-%d'))

        start = datetime.strptime(start_str, '%Y-%m-%d')
        end = datetime.strptime(end_str, '%Y-%m-%d')

        print(f"[YAHOO] Extraction avec dates: start={start.date()}, end={end.date()}")
        return extract_yahoo_data(start=start, end=end)

    @task
    def extract_documents(**context):
        """Bronze/Extract: Documents → data/documents/*.parquet"""
        # Récupérer la date de début depuis les paramètres du DAG run
        params = context.get('params', {})
        start_str = params.get('start_document', DEFAULT_DOCUMENT_START.strftime('%Y-%m-%d'))

        start = datetime.strptime(start_str, '%Y-%m-%d')

        print(f"[DOCUMENTS] Extraction avec date de début: start={start.date()}")
        return extract_eurostat_data(start=start)


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

    @task
    def transform_snapshot(mt5_parquet: str, yahoo_parquet: str, docs_parquet: str):
        """Silver/Transform: Market Snapshot → data/processed/market_snapshot_m15.parquet"""
        return transform_market_snapshot(mt5_parquet, yahoo_parquet, docs_parquet)


    # ========================================================================
    # GOLD LAYER - Load séparé
    # ========================================================================

    @task
    def load_mt5(mt5_parquet: str):
        """Gold/Load: MT5 → table mt5_eurusd_m15"""
        pipeline_run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return load_mt5_to_db(mt5_parquet, pipeline_run_id)

    @task
    def load_yahoo(yahoo_parquet: str):
        """Gold/Load: Yahoo → table yahoo_finance_daily"""
        pipeline_run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return load_yahoo_to_db(yahoo_parquet, pipeline_run_id)

    @task
    def load_documents(documents_parquet: str):
        """Gold/Load: Documents → table documents_macro"""
        pipeline_run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return load_documents_to_db(documents_parquet, pipeline_run_id)

    @task
    def load_snapshot(snapshot_parquet: str):
        """Gold/Load: Market Snapshot → table market_snapshot_m15"""
        pipeline_run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return load_market_snapshot_to_db(snapshot_parquet, pipeline_run_id)


    # ========================================================================
    # VALIDATION & NOTIFICATION
    # ========================================================================

    @task
    def validate_pipeline(mt5_result: dict, yahoo_result: dict, docs_result: dict, snapshot_loaded: dict):
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

    # Transformation snapshot (après les 3 sources)
    snapshot_features = transform_snapshot(mt5_features, yahoo_features, docs_features)

    # Load sources (parallèle)
    mt5_loaded = load_mt5(mt5_features)
    yahoo_loaded = load_yahoo(yahoo_features)
    docs_loaded = load_documents(docs_features)

    # Load snapshot (après les 3 sources chargées)
    snapshot_loaded = load_snapshot(snapshot_features)

    # Validation (après tous les loads)
    validation = validate_pipeline(mt5_loaded, yahoo_loaded, docs_loaded, snapshot_loaded)

    # Notification (après validation)
    notification = notify(validation)

    # Dependencies
    init >> [mt5_raw, yahoo_raw, docs_raw]

    # Transformations sources
    mt5_raw >> mt5_features
    yahoo_raw >> yahoo_features
    docs_raw >> docs_features

    # Transformation snapshot (nécessite les 3 sources)
    [mt5_features, yahoo_features, docs_features] >> snapshot_features

    # Load sources (parallèle)
    mt5_features >> mt5_loaded
    yahoo_features >> yahoo_loaded
    docs_features >> docs_loaded

    # Load snapshot (après transformation snapshot ET après les 3 sources chargées)
    snapshot_features >> snapshot_loaded
    [mt5_loaded, yahoo_loaded, docs_loaded] >> snapshot_loaded

    # Validation après tous les loads (y compris snapshot)
    [mt5_loaded, yahoo_loaded, docs_loaded, snapshot_loaded] >> validation >> notification

# Instancier le DAG
dag_instance = etl_forex()