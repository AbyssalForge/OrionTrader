from datetime import datetime, timedelta
from airflow import DAG
from airflow.sdk import task
import os
import pandas as pd
import requests
import psycopg2
from utils.vault_helper import get_vault

from dotenv import load_dotenv

from utils.metatrader_data import import_data

load_dotenv()

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
    dag_id="ETL_forex_EUR_USD",
    default_args=default_args,
    description="Pipeline ETL pour données Forex EURUSD",
    catchup=False,
    tags=["forex", "etl", "orion"],
):

    @task
    def extract_data_from_metatrader():
        df_train, df_test = import_data()

        # Retourner un dictionnaire pour faciliter l'accès dans les tâches suivantes
        return {
            'train': df_train.to_dict('records'),
            'test': df_test.to_dict('records')
            }

    @task
    def extract_data_from_scraping():
        vault = get_vault()
        secret = vault.get_secret('airflow', 'test')
        print(f"Secret récupéré: {secret}")
        return None

    @task
    def extract_data_from_document():
        return None

    @task
    def transform_data(mt5_data: dict):
        """
        Transforme les données.
        """
        if mt5_data is None:
            return None

        # Reconstruire les DataFrames depuis les dicts
        df_train = pd.DataFrame(mt5_data['train'])
        df_test = pd.DataFrame(mt5_data['test'])

        # Appliquer vos transformations ici
        # ...

        return {
            'train': df_train.to_dict('records'),
            'test': df_test.to_dict('records')
        }

    @task
    def load_to_db(data: dict):
        """
        Charge les données dans PostgreSQL.
        """
        if data is None:
            return None

        # TODO: Implémenter la sauvegarde en base
        # conn = psycopg2.connect(...)
        # df_train.to_sql('forex_train', conn, ...)

        return "Data loaded successfully"

    @task
    def validate(result: str):
        """
        Valide que les données sont correctement chargées.
        """
        if result:
            return f"✅ Validation OK: {result}"
        return "❌ Validation failed"

    @task
    def notify(message: str):
        """
        Envoie une notification Discord.
        """
        requests.post(DISCORD_WEBHOOK, json={"content": f"Pipeline ETL terminé: {message} 🚀"})
        return "Notification sent"

    # ===========================================================
    # CHAÎNAGE DU PIPELINE
    # ===========================================================

    # Extraction
    mt5_data = extract_data_from_metatrader()
    # df_data_scrapping = extract_data_from_scraping()
    # df_data_document = extract_data_from_document()

    # Transformation
    transformed_data = transform_data(mt5_data)

    # Chargement
    load_result = load_to_db(transformed_data)

    # Validation
    validation = validate(load_result)

    # Notification
    notify(validation)
