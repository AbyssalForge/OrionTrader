from datetime import datetime, timedelta
from airflow import DAG
from airflow.sdk import task
from airflow.utils.context import Context

import os
import pandas as pd
import requests
import psycopg2
from utils.vault_helper import get_vault

from dotenv import load_dotenv

from utils.mt5_server import import_data
from utils.alpha_vantage import get_eurusd_intraday_15min, resample_to_15min, get_dxy_daily, get_us10y_treasury_yield, get_vix_daily
from utils.document_helper import extract_documents

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
    def extract_data_from_metatrader(**context):

        base_path = "/data/mt5"
        os.makedirs(base_path, exist_ok=True)

        start = context["data_interval_start"]
        end = context["data_interval_end"]

        df = pd.DataFrame.from_dict(
            import_data(start=start, end=end)
        )

        path = f"{base_path}/eurusd_mt5.parquet"
        df.to_parquet(path)

        return path

    @task
    def extract_data_from_api():
        
        base_path = "/data/api"
        
        df_fx = get_eurusd_intraday_15min()
        df_dxy = resample_to_15min(get_dxy_daily())
        df_yield = resample_to_15min(get_us10y_treasury_yield())
        df_vix = resample_to_15min(get_vix_daily())
        
        df_fx.to_parquet(f"{base_path}/eurusd_fx.parquet")
        df_dxy.to_parquet(f"{base_path}/dxy.parquet")
        df_yield.to_parquet(f"{base_path}/us10y.parquet")
        df_vix.to_parquet(f"{base_path}/vix.parquet")
        
        return {
            "fx": f"{base_path}/eurusd_fx.parquet",
            "dxy": f"{base_path}/dxy.parquet",
            "yield": f"{base_path}/us10y.parquet",
            "vix": f"{base_path}/vix.parquet",
        }

    @task
    def extract_data_from_document():
        paths = extract_documents()
        return paths

    @task
    def transform_data(mt5_path: str, api_paths: dict, doc_paths: dict):
        """
        Merge les données MT5, API et documents.
        Crée des features simples et sauvegarde en parquet.
        """
        base_path = "/data/processed"
        os.makedirs(base_path, exist_ok=True)

        # Lecture des données
        df_mt5 = pd.read_parquet(mt5_path)
        df_fx = pd.read_parquet(api_paths["fx"])
        df_dxy = pd.read_parquet(api_paths["dxy"])
        df_yield = pd.read_parquet(api_paths["yield"])
        df_vix = pd.read_parquet(api_paths["vix"])

        df_pib = pd.read_parquet(doc_paths["pib"])
        df_cpi = pd.read_parquet(doc_paths["cpi"])
        df_events = pd.read_parquet(doc_paths["events"])

        # Assurer que toutes les dates sont en datetime
        for df in [df_mt5, df_fx, df_dxy, df_yield, df_vix]:
            df["time"] = pd.to_datetime(df["time"], utc=True)
            df.set_index("time", inplace=True)

        for df in [df_pib, df_cpi]:
            df.index = pd.to_datetime(df.index, utc=True)

        df_events["time"] = pd.to_datetime(df_events["time"], utc=True)
        df_events.set_index("time", inplace=True)

        # Merge
        # Commence par MT5
        df = df_mt5.copy()
        
        # Merge API (align 15min)
        df = df.merge(df_fx, left_index=True, right_index=True, how="left", suffixes=('', '_fx'))
        df = df.merge(df_dxy, left_index=True, right_index=True, how="left", suffixes=('', '_dxy'))
        df = df.merge(df_yield, left_index=True, right_index=True, how="left", suffixes=('', '_yield'))
        df = df.merge(df_vix, left_index=True, right_index=True, how="left", suffixes=('', '_vix'))

        # Merge documents macro
        df = df.merge(df_pib, left_index=True, right_index=True, how="left")
        df = df.merge(df_cpi, left_index=True, right_index=True, how="left")

        # Merge événements : dernier événement connu
        df_events = df_events.sort_index()
        df["event_title"] = df_events["title"].reindex(df.index, method="ffill")
        df["event_impact"] = df_events["impact"].reindex(df.index, method="ffill")

        # Features d’exemple
        df["close_diff"] = df["close"].diff()
        df["close_return"] = df["close"].pct_change()
        df["volatility_rolling"] = df["close"].rolling(window=4).std()  # approx 1h sur M15

        # Exemple feature macro : variation PIB (forward fill pour chaque ligne)
        df["pib_change"] = df["eurozone_pib"].pct_change().fillna(0)
        df["cpi_change"] = df["eurozone_cpi"].pct_change().fillna(0)

        # Sauvegarde
        out_path = os.path.join(base_path, "eurusd_features.parquet")
        df.to_parquet(out_path)

        return out_path
 

    @task
    def load_to_db(data: dict):
        return "Data loaded successfully"

    @task
    def validate(result: str):
        return "❌ Validation failed"

    @task
    def notify(message: str):
        requests.post(DISCORD_WEBHOOK, json={"content": f"Pipeline ETL terminé: {message} 🚀"})
        return "Notification sent"

    # ===========================================================
    # CHAÎNAGE DU PIPELINE
    # ===========================================================

    # Extraction
    mt5_data = extract_data_from_metatrader()
    api_data = extract_data_from_api()
    document_data = extract_data_from_document()

    # Transformation
    transformed_data = transform_data(mt5_data, api_data, document_data)

    # Chargement
    load_result = load_to_db(transformed_data)

    # Validation
    validation = validate(load_result)

    # Notification
    notify(validation)
