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

from clients.vault_helper import get_vault


def send_notification(validation_result: dict) -> dict:
    """
    Envoie une notification si DISCORD_WEBHOOK est configuré dans Vault.

    Cherche dans Vault: secret/airflow_notification -> DISCORD_WEBHOOK
    Si trouvé: envoie la notification Discord
    Sinon: skip silencieusement

    Returns:
        dict avec status de la notification
    """
    try:
        vault = get_vault()
        webhook_discord_url = vault.get_secret('Airflow_notification', 'DISCORD_WEBHOOK')

        if webhook_discord_url:
            print("[NOTIFY] DISCORD_WEBHOOK trouvé dans Vault, envoi notification...")
            return send_discord_notification(
                validation_result=validation_result,
                webhook_url=webhook_discord_url
            )
        else:
            print("[NOTIFY] DISCORD_WEBHOOK vide dans Vault, notification ignorée")
            return {"status": "skipped", "reason": "DISCORD_WEBHOOK is empty"}

    except Exception as e:
        print(f"[NOTIFY] Pas de DISCORD_WEBHOOK configuré dans Vault ({e}), notification ignorée")
        return {"status": "skipped", "reason": str(e)}

DEFAULT_DATE_NOW = datetime.now()

DEFAULT_DATE_START = DEFAULT_DATE_NOW - timedelta(days=2)
DEFAULT_DATE_END = DEFAULT_DATE_NOW - timedelta(days=1)

DEFAULT_DOCUMENT_START = DEFAULT_DATE_NOW - timedelta(days=1825)  # ~5 ans

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
        'start_mt5': DEFAULT_DATE_START.strftime('%Y-%m-%d'),
        'end_mt5': DEFAULT_DATE_END.strftime('%Y-%m-%d'),
        'start_yahoo': DEFAULT_DATE_START.strftime('%Y-%m-%d'),
        'end_yahoo': DEFAULT_DATE_END.strftime('%Y-%m-%d'),
        'start_document': DEFAULT_DOCUMENT_START.strftime('%Y-%m-%d'),
    }
)
def etl_forex():
    """
    Pipeline ETL

    Bronze (Extraction) → Silver (Transformation) → Gold (Load)
    3 sources -> 3 transformations -> 3 loads

    Composites: Calculés à l'export CSV (pas en BDD)
    """

    @task
    def initialize():
        """Bronze/Init: Créer les tables en bdd"""
        return initialize_database()

    

    @task
    def extract_mt5(**context):
        """Bronze/Extract: MT5 -> data/mt5/*.parquet"""
        params = context.get('params', {})
        start_str = params.get('start_mt5', DEFAULT_DATE_START.strftime('%Y-%m-%d'))
        end_str = params.get('end_mt5', DEFAULT_DATE_END.strftime('%Y-%m-%d'))

        start = datetime.strptime(start_str, '%Y-%m-%d')
        end = datetime.strptime(end_str, '%Y-%m-%d')

        print(f"[MT5] Extraction avec dates: start={start.date()}, end={end.date()}")
        return extract_mt5_data(start, end)

    @task
    def extract_yahoo(**context):
        """Bronze/Extract: Yahoo Finance -> data/api/*.parquet"""
        params = context.get('params', {})
        start_str = params.get('start_yahoo', DEFAULT_DATE_START.strftime('%Y-%m-%d'))
        end_str = params.get('end_yahoo', DEFAULT_DATE_END.strftime('%Y-%m-%d'))

        start = datetime.strptime(start_str, '%Y-%m-%d')
        end = datetime.strptime(end_str, '%Y-%m-%d')

        print(f"[YAHOO] Extraction avec dates: start={start.date()}, end={end.date()}")
        return extract_yahoo_data(start=start, end=end)

    @task
    def extract_documents(**context):
        """Bronze/Extract: Documents -> data/documents/*.parquet"""
        params = context.get('params', {})
        start_str = params.get('start_document', DEFAULT_DOCUMENT_START.strftime('%Y-%m-%d'))

        start = datetime.strptime(start_str, '%Y-%m-%d')

        print(f"[DOCUMENTS] Extraction avec date de début: start={start.date()}")
        return extract_eurostat_data(start=start)



    @task
    def transform_mt5(mt5_parquet: str):
        return transform_mt5_features(mt5_parquet)

    @task
    def transform_yahoo(yahoo_parquets: dict):
        return transform_yahoo_features(yahoo_parquets)

    @task
    def transform_documents(documents_parquets: dict):
        return transform_documents_features(documents_parquets)

    @task
    def transform_snapshot(mt5_parquet: str, yahoo_parquet: str, docs_parquet: str):
        return transform_market_snapshot(mt5_parquet, yahoo_parquet, docs_parquet)



    @task
    def load_mt5(mt5_parquet: str):
        pipeline_run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return load_mt5_to_db(mt5_parquet, pipeline_run_id)

    @task
    def load_yahoo(yahoo_parquet: str):
        pipeline_run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return load_yahoo_to_db(yahoo_parquet, pipeline_run_id)

    @task
    def load_documents(documents_parquet: str):
        pipeline_run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return load_documents_to_db(documents_parquet, pipeline_run_id)

    @task
    def load_snapshot(snapshot_parquet: str):
        pipeline_run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return load_market_snapshot_to_db(snapshot_parquet, pipeline_run_id)



    @task
    def validate_pipeline(mt5_result: dict, yahoo_result: dict, docs_result: dict, snapshot_loaded: dict):
        """Validation: Vérifier qualité données dans les tables"""

        validation_result = validate_data_quality(
            mt5_result=mt5_result,
            yahoo_result=yahoo_result,
            docs_result=docs_result,
            snapshot_result=snapshot_loaded
        )

        print(f"Statut global: {validation_result.get('status')}")
        print(f"Tables OK: {validation_result.get('tables_ok', 0)}/4")

        return validation_result

    @task
    def notify(validation_result: dict):
        """Notification: Envoyer résumé sur Discord (si configuré dans Vault)"""

        notification_result = send_notification(validation_result)

        print(f"Notification status: {notification_result.get('status')}")

        return notification_result



    init = initialize()

    mt5_raw = extract_mt5()
    yahoo_raw = extract_yahoo()
    docs_raw = extract_documents()

    mt5_features = transform_mt5(mt5_raw)
    yahoo_features = transform_yahoo(yahoo_raw)
    docs_features = transform_documents(docs_raw)

    snapshot_features = transform_snapshot(mt5_features, yahoo_features, docs_features)

    mt5_loaded = load_mt5(mt5_features)
    yahoo_loaded = load_yahoo(yahoo_features)
    docs_loaded = load_documents(docs_features)

    snapshot_loaded = load_snapshot(snapshot_features)

    validation = validate_pipeline(mt5_loaded, yahoo_loaded, docs_loaded, snapshot_loaded)

    notification = notify(validation)

    init >> [mt5_raw, yahoo_raw, docs_raw]

    mt5_raw >> mt5_features
    yahoo_raw >> yahoo_features
    docs_raw >> docs_features

    [mt5_features, yahoo_features, docs_features] >> snapshot_features

    mt5_features >> mt5_loaded
    yahoo_features >> yahoo_loaded
    docs_features >> docs_loaded

    snapshot_features >> snapshot_loaded
    [mt5_loaded, yahoo_loaded, docs_loaded] >> snapshot_loaded

    [mt5_loaded, yahoo_loaded, docs_loaded, snapshot_loaded] >> validation >> notification

dag_instance = etl_forex()