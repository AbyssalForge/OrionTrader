"""
ETL Forex Pipeline v4.0 - Pipeline Principal Quotidien - Architecture 100% Simplifiée

🎯 ARCHITECTURE UNIFIÉE (MT5 SUPPRIMÉ):
==================================================
📊 2 SOURCES DE DONNÉES (au lieu de 3):
  1. Yahoo Finance (UNE seule extraction):
     - EUR/USD 15m (intraday) → remplace MT5
     - 9 actifs macro daily (EUR/USD, GBP/USD, USD/JPY, DXY, S&P500, VIX, DJI, Or, Argent)

  2. Documents économiques (OECD/World Bank/ECB):
     - PIB, CPI, Events

📁 4 TABLES EN BDD:
  * forex_intraday_15m → EUR/USD 15 minutes (Yahoo)
  * yahoo_finance_daily → Indices macro quotidiens (Yahoo)
  * documents_macro → Données macro économiques
  * market_snapshot_m15 → Composites (fusion des 3 sources)

📝 Note:
  - wikipedia_indices est dans un pipeline séparé (wikipedia_scraping_pipeline)
    car les données changent rarement (exécution hebdomadaire/mensuelle/manuelle)

✅ AVANTAGES:
  - ✅ Architecture ultra-simplifiée: 2 extractions au lieu de 3
  - ✅ Plus de Docker/Wine/Pyro5/MT5 complexe
  - ✅ Une seule API (Yahoo Finance) pour forex 15m + macro daily
  - ✅ Respect des fréquences natives (15m, Daily, Monthly/Annual)
  - ✅ Parallélisation maximale
  - ✅ Plus facile à maintenir et debugger

🔄 WORKFLOW:
  Init → [Yahoo (2en1), Documents] → [Transform×3] → Snapshot → [Load×4] → Validation → Notification
"""

from airflow.sdk import dag, task
from datetime import datetime, timedelta

from services.bdd_service import initialize_database

from services.bronze_service import (
    extract_yahoo_data,  # Yahoo Finance: 15m + Daily (remplace MT5)
    extract_eurostat_data
)

from utils.trading_calendar import (
    adjust_date_range_for_trading,
    get_trading_days_info,
    is_trading_day
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
        # Si le secret n'existe pas ou erreur Vault, on skip silencieusement
        print(f"[NOTIFY] Pas de DISCORD_WEBHOOK configuré dans Vault ({e}), notification ignorée")
        return {"status": "skipped", "reason": str(e)}

# Dates par défaut (peuvent être écrasées lors du lancement manuel)
# Ces valeurs seront utilisées si aucun paramètre n'est fourni
DEFAULT_DATE_NOW = datetime.now()

# Yahoo (15m + Daily): Utiliser les derniers jours de trading (éviter week-ends)
# Importer les fonctions de calendrier pour calculer les dates par défaut
from utils.trading_calendar import get_last_trading_day

# Dernier jour de trading complet = hier (ou vendredi si on est samedi/dimanche)
DEFAULT_DATE_END = get_last_trading_day(DEFAULT_DATE_NOW - timedelta(days=1))
DEFAULT_DATE_START = DEFAULT_DATE_END - timedelta(days=1)  # J-1 (jeudi si end=vendredi)

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
        # Yahoo dates: 15m + Daily (J-1 → J, ex: jeudi → vendredi)
        'start_yahoo': DEFAULT_DATE_START.strftime('%Y-%m-%d'),
        'end_yahoo': DEFAULT_DATE_END.strftime('%Y-%m-%d'),
        # Document dates (5 ans avant → aujourd'hui)
        'start_document': DEFAULT_DOCUMENT_START.strftime('%Y-%m-%d'),
    }
)
def etl_forex():
    """
    Pipeline ETL Simplifié v4.0

    Bronze (Extraction) → Silver (Transformation) → Gold (Load)
    2 extractions → 3 transformations → 4 loads

    Flux:
    1. Bronze: Yahoo (15m+daily) + Documents
    2. Silver: Forex 15m + Yahoo Daily + Documents + Snapshot
    3. Gold: 4 tables en BDD
    4. Validation + Notification
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
    def extract_yahoo(**context):
        """
        Bronze/Extract: Yahoo Finance TOUTES SOURCES
        - EUR/USD 15m (intraday) → data/forex_intraday/eurusd_15m.parquet
        - Actifs macro daily → data/api/*.parquet (eurusd, gbpusd, dxy, spx, vix, etc.)

        Retourne: dict avec tous les chemins (eurusd_15m, eurusd, gbpusd, usdjpy, dxy, spx, vix, dji, gold, silver)
        """
        # Récupérer les dates depuis les paramètres du DAG run
        params = context.get('params', {})
        start_str = params.get('start_yahoo', DEFAULT_DATE_START.strftime('%Y-%m-%d'))
        end_str = params.get('end_yahoo', DEFAULT_DATE_END.strftime('%Y-%m-%d'))

        start = datetime.strptime(start_str, '%Y-%m-%d')
        end = datetime.strptime(end_str, '%Y-%m-%d')

        print(f"[YAHOO] Dates demandées: start={start.date()}, end={end.date()}")

        # Ajuster les dates pour éviter les week-ends
        start_adjusted, end_adjusted = adjust_date_range_for_trading(start, end)

        if start != start_adjusted or end != end_adjusted:
            print(f"[YAHOO] ⚠️  Ajustement des dates (week-end détecté):")
            print(f"[YAHOO]    start: {start.date()} → {start_adjusted.date()}")
            print(f"[YAHOO]    end:   {end.date()} → {end_adjusted.date()}")

        # Afficher info sur les jours de trading
        trading_info = get_trading_days_info(start, end)
        print(f"[YAHOO] Jours de trading dans la plage: {trading_info['trading_days_count']}")

        print(f"[YAHOO] Extraction TOUTES SOURCES (dates ajustées)")
        return extract_yahoo_data(start=start_adjusted, end=end_adjusted, include_intraday=True)

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
    def transform_forex_intraday(yahoo_all: dict):
        """Silver/Transform: EUR/USD 15m (Yahoo) → data/processed/forex_intraday_features.parquet"""
        # Extraire le chemin EUR/USD 15m du dictionnaire Yahoo
        eurusd_15m_path = yahoo_all.get('eurusd_15m')
        if not eurusd_15m_path:
            raise ValueError("EUR/USD 15m non trouvé dans les données Yahoo")
        return transform_mt5_features(eurusd_15m_path)

    @task
    def transform_yahoo(yahoo_all: dict):
        """Silver/Transform: Yahoo Daily (macro) → data/processed/yahoo_features.parquet"""
        # Extraire uniquement les actifs daily (exclure eurusd_15m)
        yahoo_daily = {k: v for k, v in yahoo_all.items() if k != 'eurusd_15m'}
        return transform_yahoo_features(yahoo_daily)

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
    def load_forex_intraday(forex_intraday_parquet: str):
        """Gold/Load: EUR/USD 15m (Yahoo) → table forex_intraday_15m"""
        pipeline_run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return load_mt5_to_db(forex_intraday_parquet, pipeline_run_id)

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
        """Validation: Vérifier qualité données dans les 4 tables"""
        print("[VALIDATE] ==================== VALIDATION ====================")

        # Consolider les résultats des 4 loads
        validation_result = validate_data_quality(
            mt5_result=mt5_result,
            yahoo_result=yahoo_result,
            docs_result=docs_result,
            snapshot_result=snapshot_loaded
        )

        total_tables = validation_result.get('tables_ok', 0)

        print(f"[VALIDATE] Statut global: {validation_result.get('status')}")
        print(f"[VALIDATE] Tables OK: {total_tables}/4")
        print("[VALIDATE] Note: Wikipedia est dans un pipeline séparé")
        print("[VALIDATE] ==================== FIN ====================")

        return validation_result

    @task
    def notify(validation_result: dict):
        """Notification: Envoyer résumé sur Discord (si configuré dans Vault)"""
        print("[NOTIFY] ==================== NOTIFICATION ====================")

        notification_result = send_notification(validation_result)

        print(f"[NOTIFY] Notification status: {notification_result.get('status')}")
        print("[NOTIFY] ==================== FIN ====================")

        return notification_result


    # ========================================================================
    # DÉFINITION DU WORKFLOW SIMPLIFIÉ
    # ========================================================================

    # Init
    init = initialize()

    # Extraction (parallèle) - SIMPLIFIÉ: 2 sources au lieu de 3
    yahoo_all_raw = extract_yahoo()         # Yahoo 15m + Daily (remplace MT5 + Yahoo séparés)
    docs_raw = extract_documents()          # Documents économiques

    # Transformation sources (parallèle) - 3 transformations
    forex_intraday_features = transform_forex_intraday(yahoo_all_raw)  # EUR/USD 15m
    yahoo_daily_features = transform_yahoo(yahoo_all_raw)              # Actifs macro daily
    docs_features = transform_documents(docs_raw)                      # Documents

    # Transformation snapshot (après les 3 transformations principales)
    snapshot_features = transform_snapshot(forex_intraday_features, yahoo_daily_features, docs_features)

    # Load sources (parallèle) - 3 loads
    forex_intraday_loaded = load_forex_intraday(forex_intraday_features)
    yahoo_daily_loaded = load_yahoo(yahoo_daily_features)
    docs_loaded = load_documents(docs_features)

    # Load snapshot (après les 3 sources principales chargées)
    snapshot_loaded = load_snapshot(snapshot_features)

    # Validation (après tous les loads)
    validation = validate_pipeline(forex_intraday_loaded, yahoo_daily_loaded, docs_loaded, snapshot_loaded)

    # Notification (après validation)
    notification = notify(validation)

    # ========================================================================
    # DÉPENDANCES
    # ========================================================================

    # Init → Extractions (parallèle)
    init >> [yahoo_all_raw, docs_raw]

    # Extractions → Transformations (parallèle)
    yahoo_all_raw >> [forex_intraday_features, yahoo_daily_features]
    docs_raw >> docs_features

    # Transformations → Snapshot (nécessite les 3)
    [forex_intraday_features, yahoo_daily_features, docs_features] >> snapshot_features

    # Transformations → Loads (parallèle)
    forex_intraday_features >> forex_intraday_loaded
    yahoo_daily_features >> yahoo_daily_loaded
    docs_features >> docs_loaded

    # Snapshot → Load snapshot (après transformation ET après les 3 sources principales chargées)
    snapshot_features >> snapshot_loaded
    [forex_intraday_loaded, yahoo_daily_loaded, docs_loaded] >> snapshot_loaded

    # Tous les loads → Validation → Notification
    [forex_intraday_loaded, yahoo_daily_loaded, docs_loaded, snapshot_loaded] >> validation >> notification

# Instancier le DAG
dag_instance = etl_forex()