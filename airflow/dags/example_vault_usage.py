"""
Exemple d'utilisation de HashiCorp Vault dans un DAG Airflow
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import os
import hvac


def get_secret_from_vault_direct():
    """
    Méthode 1: Accès direct à Vault avec hvac
    Utile quand vous voulez un contrôle total
    """
    # Connexion à Vault
    vault_addr = os.getenv('VAULT_ADDR', 'http://vault:8200')
    vault_token = os.getenv('VAULT_TOKEN', 'orion-root-token')

    client = hvac.Client(url=vault_addr, token=vault_token)

    # Vérifier l'authentification
    if not client.is_authenticated():
        raise Exception("Failed to authenticate with Vault")

    # Lire un secret
    secret = client.secrets.kv.v2.read_secret_version(path='api/keys')
    api_key = secret['data']['data']['api_key']

    print(f"✅ API Key récupérée: {api_key[:5]}...")
    return api_key


def get_multiple_secrets():
    """
    Exemple: Récupérer plusieurs secrets d'un coup
    """
    vault_addr = os.getenv('VAULT_ADDR', 'http://vault:8200')
    vault_token = os.getenv('VAULT_TOKEN', 'orion-root-token')

    client = hvac.Client(url=vault_addr, token=vault_token)

    # Récupérer les credentials MT5
    mt5_secrets = client.secrets.kv.v2.read_secret_version(path='api/mt5')
    mt5_data = mt5_secrets['data']['data']

    print(f"MT5 Server: {mt5_data['server']}")
    print(f"MT5 Login: {mt5_data['login']}")
    print(f"MT5 Password: {'*' * len(mt5_data['password'])}")

    # Récupérer la config MLflow
    mlflow_secrets = client.secrets.kv.v2.read_secret_version(path='mlflow/config')
    mlflow_uri = mlflow_secrets['data']['data']['tracking_uri']

    print(f"MLflow URI: {mlflow_uri}")

    return {
        'mt5': mt5_data,
        'mlflow_uri': mlflow_uri
    }


def use_secret_in_trading_logic(**context):
    """
    Exemple: Utiliser les secrets dans une logique de trading
    """
    vault_addr = os.getenv('VAULT_ADDR', 'http://vault:8200')
    vault_token = os.getenv('VAULT_TOKEN', 'orion-root-token')

    client = hvac.Client(url=vault_addr, token=vault_token)

    # Récupérer les credentials MT5
    mt5_secrets = client.secrets.kv.v2.read_secret_version(path='api/mt5')
    mt5_creds = mt5_secrets['data']['data']

    # Simuler une connexion MT5 (ne pas exécuter réellement ici)
    print(f"🔌 Connexion à MetaTrader5...")
    print(f"   Server: {mt5_creds['server']}")
    print(f"   Login: {mt5_creds['login']}")

    # Récupérer les clés API pour un service externe
    api_secrets = client.secrets.kv.v2.read_secret_version(path='api/keys')
    api_key = api_secrets['data']['data']['api_key']

    print(f"🔑 API Key chargée: {api_key[:10]}...")

    # Ici vous pourriez utiliser ces credentials pour:
    # - Se connecter à MT5
    # - Appeler une API externe
    # - Envoyer des notifications

    return "Trading logic executed successfully"


def send_notification_with_webhook(**context):
    """
    Exemple: Envoyer une notification Discord avec le webhook stocké dans Vault
    """
    import requests

    vault_addr = os.getenv('VAULT_ADDR', 'http://vault:8200')
    vault_token = os.getenv('VAULT_TOKEN', 'orion-root-token')

    client = hvac.Client(url=vault_addr, token=vault_token)

    # Récupérer le webhook Discord
    discord_secrets = client.secrets.kv.v2.read_secret_version(path='api/discord')
    webhook_url = discord_secrets['data']['data']['webhook_url']

    # Envoyer un message
    message = {
        "content": "✅ Pipeline Airflow exécutée avec succès!",
        "embeds": [{
            "title": "OrionTrader - Notification",
            "description": "Le DAG de test Vault s'est exécuté correctement",
            "color": 3066993  # Vert
        }]
    }

    response = requests.post(webhook_url, json=message)

    if response.status_code == 204:
        print("✅ Notification envoyée à Discord")
    else:
        print(f"❌ Erreur lors de l'envoi: {response.status_code}")

    return "Notification sent"


def create_secret_in_vault(**context):
    """
    Exemple: Créer ou mettre à jour un secret dans Vault
    Utile pour stocker des résultats de pipeline
    """
    vault_addr = os.getenv('VAULT_ADDR', 'http://vault:8200')
    vault_token = os.getenv('VAULT_TOKEN', 'orion-root-token')

    client = hvac.Client(url=vault_addr, token=vault_token)

    # Créer un nouveau secret avec les résultats du pipeline
    pipeline_results = {
        'last_run': datetime.now().isoformat(),
        'status': 'success',
        'trades_executed': 42,
        'profit': '1234.56'
    }

    client.secrets.kv.v2.create_or_update_secret(
        path='airflow/pipeline-results',
        secret=pipeline_results
    )

    print("✅ Résultats du pipeline sauvegardés dans Vault")
    print(f"   Path: secret/airflow/pipeline-results")

    return pipeline_results


# Définition du DAG
with DAG(
    'example_vault_usage',
    description='Exemple d\'utilisation de HashiCorp Vault dans Airflow',
    schedule=None,  # Exécution manuelle
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['example', 'vault', 'security'],
) as dag:

    # Task 1: Récupérer un secret simple
    task_get_secret = PythonOperator(
        task_id='get_api_key_from_vault',
        python_callable=get_secret_from_vault_direct
    )

    # Task 2: Récupérer plusieurs secrets
    task_get_multiple = PythonOperator(
        task_id='get_multiple_secrets',
        python_callable=get_multiple_secrets
    )

    # Task 3: Utiliser les secrets dans la logique métier
    task_trading_logic = PythonOperator(
        task_id='use_secrets_in_trading',
        python_callable=use_secret_in_trading_logic
    )

    # Task 4: Envoyer une notification
    task_notification = PythonOperator(
        task_id='send_discord_notification',
        python_callable=send_notification_with_webhook
    )

    # Task 5: Créer/Mettre à jour un secret
    task_create_secret = PythonOperator(
        task_id='save_pipeline_results',
        python_callable=create_secret_in_vault
    )

    # Définir l'ordre d'exécution
    task_get_secret >> task_get_multiple >> task_trading_logic >> task_create_secret >> task_notification
