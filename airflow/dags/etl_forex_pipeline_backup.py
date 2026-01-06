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
from utils.alpha_vantage import get_macro_context_stooq
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

        base_path = "data/mt5"
        os.makedirs(base_path, exist_ok=True)

        # Valeurs par défaut : 30 jours de données
        now = datetime.now()
        default_start = now - timedelta(days=30)
        default_end = now

        start = context.get("data_interval_start")
        end = context.get("data_interval_end")

        # Si les dates du contexte sont None ou identiques (DAG manuel sans schedule),
        # utiliser les valeurs par défaut
        if start is None or end is None or start == end:
            start = default_start
            end = default_end
            print(f"[DAG] Utilisation des dates par défaut (contexte non disponible ou DAG manuel)")
            print(f"[DAG] Période: {start} -> {end}")
        else:
            print(f"[DAG] Utilisation des dates du contexte Airflow")
            print(f"[DAG] Période: {start} -> {end}")

        df = pd.DataFrame.from_dict(
            import_data(start=start, end=end)
        )

        path = f"{base_path}/eurusd_mt5.parquet"
        df.to_parquet(path)

        return path

    @task
    def extract_data_from_api():
        """
        Récupère le contexte macro via Stooq (GRATUIT)
        - EUR/USD, GBP/USD, USD/JPY (Forex daily)
        - DXY, S&P 500, VIX, Dow Jones (Indices daily)
        - Or, Argent (Commodities daily)
        """
        base_path = "data/api"
        os.makedirs(base_path, exist_ok=True)

        # Récupérer tout le contexte macro en une fois (365 jours)
        print("[DAG] Récupération du contexte macro via Stooq...")
        macro_context = get_macro_context_stooq(days=365)

        # Sauvegarder chaque actif en parquet (seulement ceux disponibles)
        paths = {}

        asset_mapping = {
            'eurusd': 'EUR/USD',
            'gbpusd': 'GBP/USD',
            'usdjpy': 'USD/JPY',
            'dxy': 'DXY (Dollar Index)',
            'spx': 'S&P 500',
            'vix': 'VIX',
            'dji': 'Dow Jones',
            'gold': 'Or (Gold)',
            'silver': 'Argent (Silver)'
        }

        for key, name in asset_mapping.items():
            if key in macro_context:
                print(f"[DAG] Sauvegarde {name}...")
                file_path = f"{base_path}/{key}_daily.parquet"
                macro_context[key].to_parquet(file_path)
                paths[key] = file_path
            else:
                print(f"[DAG] ⚠ {name} non disponible, ignoré")

        print(f"[DAG] ✓ {len(paths)} actifs macro sauvegardés")

        return paths

    @task
    def extract_data_from_document(**context):
        # Valeurs par défaut : 30 jours de données (même logique que MT5)
        now = datetime.now()
        default_start = now - timedelta(days=30)
        default_end = now

        start = context.get("data_interval_start")
        end = context.get("data_interval_end")

        # Si les dates du contexte sont None ou identiques (DAG manuel sans schedule),
        # utiliser les valeurs par défaut
        if start is None or end is None or start == end:
            start = default_start
            end = default_end
            print(f"[DAG] Documents - Utilisation des dates par défaut")
            print(f"[DAG] Documents - Période: {start} -> {end}")
        else:
            print(f"[DAG] Documents - Utilisation des dates du contexte Airflow")
            print(f"[DAG] Documents - Période: {start} -> {end}")

        paths = extract_documents()
        return paths

    @task
    def transform_data(mt5_path: str, api_paths: dict, doc_paths: dict):
        """
        Merge les données MT5 (intraday M15) avec le contexte macro Stooq (daily)
        et les documents macro.

        Données daily Stooq sont resample en M15 via forward-fill.
        """
        base_path = "/data/processed"
        os.makedirs(base_path, exist_ok=True)

        # Lecture des données MT5 (M15)
        df_mt5 = pd.read_parquet(mt5_path)
        if 'time' not in df_mt5.columns:
            df_mt5 = df_mt5.reset_index()
        df_mt5['time'] = pd.to_datetime(df_mt5['time'], utc=True)
        df_mt5 = df_mt5.set_index('time').sort_index()

        # Lecture des données Stooq (daily) - contexte macro
        print("[TRANSFORM] Lecture des données macro Stooq...")

        # Lire seulement les actifs disponibles
        macro_dfs = {}

        asset_names = {
            'eurusd': 'eurusd_daily',
            'gbpusd': 'gbpusd_daily',
            'usdjpy': 'usdjpy_daily',
            'dxy': 'dxy',
            'spx': 'spx',
            'vix': 'vix',
            'dji': 'dji',
            'gold': 'gold',
            'silver': 'silver'
        }

        for key, display_name in asset_names.items():
            if key in api_paths:
                try:
                    df = pd.read_parquet(api_paths[key])
                    macro_dfs[display_name] = df
                    print(f"[TRANSFORM] ✓ {display_name} chargé")
                except Exception as e:
                    print(f"[TRANSFORM] ⚠ Erreur lecture {display_name}: {e}")
            else:
                print(f"[TRANSFORM] ⚠ {display_name} non disponible")

        # Resample daily -> M15 via forward-fill
        print(f"[TRANSFORM] Resample {len(macro_dfs)} actifs daily -> M15 (forward-fill)...")

        # Resample chaque dataframe daily en M15
        for name, df_macro in macro_dfs.items():
            df_macro.index = pd.to_datetime(df_macro.index, utc=True)
            # Resample à M15 et forward-fill les valeurs daily
            df_resampled = df_macro.resample('15T').ffill()

            # Renommer les colonnes pour éviter les conflits
            df_resampled.columns = [f"{name}_{col}" for col in df_resampled.columns]

            # Merge avec MT5
            df_mt5 = df_mt5.merge(df_resampled, left_index=True, right_index=True, how='left')

        # Lecture documents macro
        print("[TRANSFORM] Lecture documents macro...")
        df_pib = pd.read_parquet(doc_paths["pib"])
        df_cpi = pd.read_parquet(doc_paths["cpi"])
        df_events = pd.read_parquet(doc_paths["events"])

        df_pib.index = pd.to_datetime(df_pib.index, utc=True)
        df_cpi.index = pd.to_datetime(df_cpi.index, utc=True)
        df_events['time'] = pd.to_datetime(df_events['time'], utc=True)
        df_events = df_events.set_index('time').sort_index()

        # Merge documents (forward-fill)
        df_mt5 = df_mt5.merge(df_pib.resample('15T').ffill(), left_index=True, right_index=True, how='left')
        df_mt5 = df_mt5.merge(df_cpi.resample('15T').ffill(), left_index=True, right_index=True, how='left')

        # Merge événements : dernier événement connu
        df_mt5["event_title"] = df_events["title"].reindex(df_mt5.index, method="ffill")
        df_mt5["event_impact"] = df_events["impact"].reindex(df_mt5.index, method="ffill")

        # ===== FEATURES ENGINEERING =====
        print("[TRANSFORM] Création des features...")

        # Features price action MT5
        df_mt5["close_diff"] = df_mt5["close"].diff()
        df_mt5["close_return"] = df_mt5["close"].pct_change()
        df_mt5["volatility_1h"] = df_mt5["close"].rolling(window=4).std()  # 1h sur M15

        # Features macro
        if 'dxy_close' in df_mt5.columns:
            df_mt5["dxy_trend"] = df_mt5["dxy_close"].pct_change(periods=4)  # Trend 1h

        if 'vix_close' in df_mt5.columns:
            df_mt5["vix_level"] = df_mt5["vix_close"]  # Niveau de stress

        if 'spx_close' in df_mt5.columns:
            df_mt5["spx_trend"] = df_mt5["spx_close"].pct_change(periods=4)  # Risk-on/off

        if 'gold_close' in df_mt5.columns:
            df_mt5["gold_trend"] = df_mt5["gold_close"].pct_change(periods=4)  # Safe haven

        # Features documents
        if 'eurozone_pib' in df_mt5.columns:
            df_mt5["pib_change"] = df_mt5["eurozone_pib"].pct_change().fillna(0)

        if 'eurozone_cpi' in df_mt5.columns:
            df_mt5["cpi_change"] = df_mt5["eurozone_cpi"].pct_change().fillna(0)

        # Sauvegarde
        out_path = os.path.join(base_path, "eurusd_features.parquet")
        df_mt5.to_parquet(out_path)

        print(f"[TRANSFORM] ✓ Features créées: {df_mt5.shape[0]} lignes, {df_mt5.shape[1]} colonnes")
        print(f"[TRANSFORM] ✓ Sauvegardé: {out_path}")

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
    #notify(validation)
