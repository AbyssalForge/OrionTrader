"""
Wikipedia Scraping Pipeline - Référentiel Indices Boursiers

Pipeline indépendant pour scraper les composants des indices boursiers depuis Wikipedia.
Ce pipeline est séparé du pipeline ETL principal car les données changent rarement.

Fréquence recommandée: Hebdomadaire ou Manuel
Indices scrapés: CAC 40, S&P 500, NASDAQ 100, Dow Jones
Volume attendu: ~670 tickers uniques
"""

from airflow.sdk import dag, task
from datetime import datetime, timedelta

from services.bdd_service import initialize_database
from services.bronze_service import extract_wikipedia_indices
from services.silver_service import transform_wikipedia_features
from services.gold_service import load_wikipedia_to_db
from services.validation_service import send_wikipedia_notification
from clients.vault_helper import get_vault


# DAG CONFIG
default_args = {
    'owner': 'orion',
    'email_on_failure': True,
    'email': 'admin@oriontrader.ai',
    'retries': 2,
    'retry_delay': timedelta(minutes=3)
}

@dag(
    dag_id='wikipedia_scraping_pipeline',
    default_args=default_args,
    description="Scraping Wikipedia - Référentiel indices boursiers (CAC40, SP500, NASDAQ100, DJIA)",
    schedule=None,  # Manuel - à exécuter manuellement ou planifier hebdomadaire/mensuel
    # schedule='0 2 * * 0',  # Optionnel: Dimanche à 2h00 UTC (hebdomadaire)
    # schedule='0 2 1 * *',  # Optionnel: 1er du mois à 2h00 UTC (mensuel)
    catchup=False,
    tags=['wikipedia', 'scraping', 'reference'],
)
def wikipedia_scraping():
    """
    Pipeline de scraping Wikipedia

    Bronze (Scraping) → Silver (Transformation) → Gold (Load)

    Résultat: Table wikipedia_indices avec mapping ticker → secteur
    """

    # ========================================================================
    # INITIALISATION
    # ========================================================================

    @task
    def initialize():
        """Init: Créer la table wikipedia_indices si elle n'existe pas"""
        print("[INIT] Initialisation de la base de données...")
        return initialize_database()


    # ========================================================================
    # BRONZE LAYER - Extraction
    # ========================================================================

    @task
    def extract_wikipedia():
        """Bronze/Extract: Wikipedia → data/wikipedia/*.parquet"""
        print("[WIKIPEDIA] ==================== SCRAPING ====================")
        print("[WIKIPEDIA] Scraping 4 indices boursiers depuis Wikipedia:")
        print("[WIKIPEDIA]   - CAC 40 (France)")
        print("[WIKIPEDIA]   - S&P 500 (USA)")
        print("[WIKIPEDIA]   - NASDAQ 100 (USA)")
        print("[WIKIPEDIA]   - Dow Jones Industrial Average (USA)")

        result = extract_wikipedia_indices()

        # Log des statistiques
        total_companies = sum(len(df) for df in result.values() if df is not None)
        print(f"[WIKIPEDIA] Total companies scraped: {total_companies}")
        print("[WIKIPEDIA] ==================== FIN SCRAPING ====================")

        return result


    # ========================================================================
    # SILVER LAYER - Transformation
    # ========================================================================

    @task
    def transform_wikipedia(wikipedia_parquets: dict):
        """Silver/Transform: Wikipedia → data/processed/wikipedia_indices.parquet"""
        print("[TRANSFORM] ==================== TRANSFORMATION ====================")
        print("[TRANSFORM] Nettoyage et consolidation des données Wikipedia...")

        result = transform_wikipedia_features(wikipedia_parquets)

        print("[TRANSFORM] Transformations appliquées:")
        print("[TRANSFORM]   - Nettoyage des tickers")
        print("[TRANSFORM]   - Standardisation des secteurs")
        print("[TRANSFORM]   - Dédoublonnage (premier indice conservé)")
        print("[TRANSFORM]   - Ajout région (Europe, North America)")
        print("[TRANSFORM]   - Indicateur multi-indices")
        print("[TRANSFORM] ==================== FIN TRANSFORMATION ====================")

        return result


    # ========================================================================
    # GOLD LAYER - Load
    # ========================================================================

    @task
    def load_wikipedia(wikipedia_parquet: str):
        """Gold/Load: Wikipedia → table wikipedia_indices"""
        print("[LOAD] ==================== CHARGEMENT BDD ====================")

        pipeline_run_id = f"wiki_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result = load_wikipedia_to_db(wikipedia_parquet, pipeline_run_id)

        if result.get('status') == 'success':
            print(f"[LOAD] ✅ Wikipedia chargé avec succès: {result.get('rows', 0)} tickers")
        else:
            print(f"[LOAD] ❌ Erreur lors du chargement: {result.get('error', 'Unknown')}")

        print("[LOAD] ==================== FIN CHARGEMENT ====================")

        return result


    # ========================================================================
    # VALIDATION
    # ========================================================================

    @task
    def validate_wikipedia(load_result: dict):
        """Validation: Vérifier qualité des données Wikipedia"""
        print("[VALIDATE] ==================== VALIDATION ====================")

        validation_result = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'pipeline': 'wikipedia_scraping'
        }

        if load_result.get('status') == 'success':
            rows = load_result.get('rows', 0)
            validation_result['wikipedia_ok'] = True
            validation_result['wikipedia_rows'] = rows

            # Vérifications de qualité
            if rows < 600:
                validation_result['warning'] = f"Nombre de tickers faible: {rows} (attendu ~670)"
            elif rows > 800:
                validation_result['warning'] = f"Nombre de tickers élevé: {rows} (attendu ~670)"
            else:
                validation_result['quality'] = 'excellent'

            print(f"[VALIDATE] ✅ Validation réussie: {rows} tickers chargés")

        else:
            validation_result['status'] = 'failed'
            validation_result['wikipedia_ok'] = False
            validation_result['error'] = load_result.get('error', 'Unknown error')
            print(f"[VALIDATE] ❌ Validation échouée: {validation_result['error']}")

        print("[VALIDATE] ==================== FIN VALIDATION ====================")

        return validation_result


    # ========================================================================
    # NOTIFICATION
    # ========================================================================

    @task
    def notify_wikipedia(validation_result: dict):
        """Notification: Envoyer résumé sur Discord (si configuré dans Vault)"""
        print("[NOTIFY] ==================== NOTIFICATION ====================")

        try:
            vault = get_vault()
            webhook_discord_url = vault.get_secret('orionTrader', 'DISCORD_WEBHOOK')

            if webhook_discord_url:
                print("[NOTIFY] DISCORD_WEBHOOK trouvé dans Vault, envoi notification...")
                notification_result = send_wikipedia_notification(
                    validation_result=validation_result,
                    webhook_url=webhook_discord_url
                )
                print(f"[NOTIFY] Status: {notification_result.get('status')}")
            else:
                print("[NOTIFY] DISCORD_WEBHOOK vide dans Vault, notification ignorée")
                notification_result = {"status": "skipped", "reason": "No webhook"}

        except Exception as e:
            print(f"[NOTIFY] Pas de DISCORD_WEBHOOK dans Vault ({e}), notification ignorée")
            notification_result = {"status": "skipped", "reason": str(e)}

        print("[NOTIFY] ==================== FIN NOTIFICATION ====================")

        return notification_result


    # ========================================================================
    # DÉFINITION DU WORKFLOW
    # ========================================================================

    # Init
    init = initialize()

    # Extraction
    wiki_raw = extract_wikipedia()

    # Transformation
    wiki_features = transform_wikipedia(wiki_raw)

    # Load
    wiki_loaded = load_wikipedia(wiki_features)

    # Validation
    validation = validate_wikipedia(wiki_loaded)

    # Notification
    notification = notify_wikipedia(validation)

    # Dependencies
    init >> wiki_raw >> wiki_features >> wiki_loaded >> validation >> notification


# Instancier le DAG
dag_instance = wikipedia_scraping()
