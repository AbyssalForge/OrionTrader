"""
Exemple SIMPLE : Comment récupérer des secrets Vault dans Airflow
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from utils.vault_helper import get_vault


# ═══════════════════════════════════════════════════════════════════════
# MÉTHODE 1: Récupérer UN secret simple (recommandé)
# ═══════════════════════════════════════════════════════════════════════

def exemple_1_secret_simple():
    """Récupérer une seule clé d'un secret"""
    vault = get_vault()

    # Récupérer juste l'API key de Binance
    api_key = vault.get_secret('api/binance', 'api_key')

    print(f"✅ API Key récupérée: {api_key[:5]}...")
    return api_key


# ═══════════════════════════════════════════════════════════════════════
# MÉTHODE 2: Récupérer TOUTES les clés d'un secret
# ═══════════════════════════════════════════════════════════════════════

def exemple_2_secret_complet():
    """Récupérer toutes les clés d'un secret"""
    vault = get_vault()

    # Récupérer tout le secret MT5
    mt5_creds = vault.get_secret('api/mt5')

    print(f"Login: {mt5_creds['login']}")
    print(f"Server: {mt5_creds['server']}")
    print(f"Password: {'*' * len(mt5_creds['password'])}")

    return mt5_creds


# ═══════════════════════════════════════════════════════════════════════
# MÉTHODE 3: Récupérer PLUSIEURS secrets
# ═══════════════════════════════════════════════════════════════════════

def exemple_3_plusieurs_secrets():
    """Récupérer plusieurs secrets différents"""
    vault = get_vault()

    # Récupérer plusieurs secrets
    binance_key = vault.get_secret('api/binance', 'api_key')
    mt5_login = vault.get_secret('api/mt5', 'login')
    mlflow_uri = vault.get_secret('mlflow/config', 'tracking_uri')

    print(f"Binance API Key: {binance_key[:5]}...")
    print(f"MT5 Login: {mt5_login}")
    print(f"MLflow URI: {mlflow_uri}")

    return {
        'binance_key': binance_key,
        'mt5_login': mt5_login,
        'mlflow_uri': mlflow_uri
    }


# ═══════════════════════════════════════════════════════════════════════
# MÉTHODE 4: Utiliser dans une logique métier
# ═══════════════════════════════════════════════════════════════════════

def exemple_4_usage_reel(**context):
    """Exemple d'utilisation réelle dans une logique de trading"""
    vault = get_vault()

    # 1. Récupérer les credentials MT5
    mt5_creds = vault.get_secret('api/mt5')

    print(f"🔌 Connexion à MetaTrader5...")
    print(f"   Server: {mt5_creds['server']}")
    print(f"   Login: {mt5_creds['login']}")

    # 2. Récupérer l'API key pour un service externe
    binance_creds = vault.get_secret('api/binance')

    print(f"🔑 Connexion à Binance...")
    print(f"   API Key: {binance_creds['api_key'][:10]}...")

    # 3. Simuler une logique de trading
    print(f"📊 Exécution de la stratégie de trading...")

    # Ici vous utiliseriez vraiment les credentials:
    # - mt5.login(mt5_creds['login'], mt5_creds['password'], mt5_creds['server'])
    # - client = BinanceClient(api_key, api_secret)

    return "Trading logic executed"


# ═══════════════════════════════════════════════════════════════════════
# MÉTHODE 5: Sauvegarder des résultats dans Vault
# ═══════════════════════════════════════════════════════════════════════

def exemple_5_sauvegarder_resultats(**context):
    """Sauvegarder les résultats d'une pipeline dans Vault"""
    vault = get_vault()

    # Sauvegarder les résultats
    vault.set_secret(
        'airflow/last-run',
        timestamp=datetime.now().isoformat(),
        status='success',
        trades_executed=42,
        profit=1234.56,
        strategy='momentum'
    )

    print("✅ Résultats sauvegardés dans Vault")
    print("   Path: secret/airflow/last-run")

    # Relire pour vérifier
    results = vault.get_secret('airflow/last-run')
    print(f"   Timestamp: {results['timestamp']}")
    print(f"   Profit: {results['profit']}")

    return results


# ═══════════════════════════════════════════════════════════════════════
# MÉTHODE 6: Passer les secrets entre tasks
# ═══════════════════════════════════════════════════════════════════════

def exemple_6a_recuperer_secret(**context):
    """Task 1: Récupérer un secret"""
    vault = get_vault()
    api_key = vault.get_secret('api/binance', 'api_key')

    # Passer à la task suivante via XCom
    context['ti'].xcom_push(key='api_key', value=api_key)

    print(f"✅ Secret récupéré et transmis via XCom")
    return api_key


def exemple_6b_utiliser_secret(**context):
    """Task 2: Utiliser le secret reçu"""
    # Récupérer depuis XCom
    api_key = context['ti'].xcom_pull(
        task_ids='recuperer_secret',
        key='api_key'
    )

    print(f"✅ Secret reçu via XCom: {api_key[:5]}...")

    # Utiliser l'API key
    print(f"📡 Appel API avec la clé...")

    return "API call completed"


# ═══════════════════════════════════════════════════════════════════════
# DÉFINITION DU DAG
# ═══════════════════════════════════════════════════════════════════════

with DAG(
    'simple_vault_example',
    description='Exemples SIMPLES d\'utilisation de Vault',
    schedule=None,  # Exécution manuelle
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['example', 'vault', 'simple'],
) as dag:

    # Exemple 1: Un secret simple
    task1 = PythonOperator(
        task_id='exemple_1_secret_simple',
        python_callable=exemple_1_secret_simple
    )

    # Exemple 2: Secret complet
    task2 = PythonOperator(
        task_id='exemple_2_secret_complet',
        python_callable=exemple_2_secret_complet
    )

    # Exemple 3: Plusieurs secrets
    task3 = PythonOperator(
        task_id='exemple_3_plusieurs_secrets',
        python_callable=exemple_3_plusieurs_secrets
    )

    # Exemple 4: Usage réel
    task4 = PythonOperator(
        task_id='exemple_4_usage_reel',
        python_callable=exemple_4_usage_reel
    )

    # Exemple 5: Sauvegarder
    task5 = PythonOperator(
        task_id='exemple_5_sauvegarder',
        python_callable=exemple_5_sauvegarder_resultats
    )

    # Exemple 6: Passer entre tasks
    task6a = PythonOperator(
        task_id='recuperer_secret',
        python_callable=exemple_6a_recuperer_secret
    )

    task6b = PythonOperator(
        task_id='utiliser_secret',
        python_callable=exemple_6b_utiliser_secret
    )

    # Ordre d'exécution
    task1 >> task2 >> task3 >> task4 >> task5 >> task6a >> task6b
