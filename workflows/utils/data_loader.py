import MetaTrader5 as mt5
import pandas as pd
import os
import time
from prefect import get_run_logger
from dotenv import load_dotenv

load_dotenv()

SYMBOL = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_M15
START = pd.Timestamp("2023-01-01")
END = pd.Timestamp("2025-11-01")
PARQUET_PATH = f"data/{SYMBOL.lower()}_{TIMEFRAME}.parquet"

MT5_LOGIN = int(os.environ.get('MT5_LOGIN'))
MT5_PASSWORD = os.environ.get('MT5_PASSWORD')
MT5_SERVER = os.environ.get('MT5_SERVER')


def connect_mt5(max_retries=3, wait_time=2):
    """Connexion robuste à MetaTrader 5"""
    logger = get_run_logger()
    mt5.shutdown()
    time.sleep(1)

    for attempt in range(1, max_retries + 1):
        logger.info(f"Tentative {attempt}/{max_retries} de connexion à MT5...")
        if not mt5.initialize():
            err = mt5.last_error()
            logger.error(f"Échec MT5 : {err}")
            time.sleep(wait_time)
            continue

        if MT5_LOGIN:
            if not mt5.login(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
                err = mt5.last_error()
                logger.error(f"Connexion échouée : {err}")
                mt5.shutdown()
                time.sleep(wait_time)
                continue

        logger.info("✅ Connexion réussie à MetaTrader 5.")
        return True

    logger.error("❌ Impossible de se connecter à MetaTrader 5.")
    return False


def import_data():
    """
    Télécharge les données depuis MT5 ou charge depuis cache local.
    Retourne un DataFrame avec colonnes open, high, low, close.
    """
    logger = get_run_logger()

    # 🔹 Si fichier existant → on le réutilise
    if os.path.exists(PARQUET_PATH):
        logger.info(f"📁 Chargement des données existantes depuis {PARQUET_PATH}")
        df = pd.read_parquet(PARQUET_PATH)

    else:
        logger.info("🌐 Téléchargement des données depuis MetaTrader 5...")
        if not connect_mt5():
            raise RuntimeError("Impossible de se connecter à MetaTrader 5.")

        rates = mt5.copy_rates_range(SYMBOL, TIMEFRAME, START.to_pydatetime(), END.to_pydatetime())
        if rates is None or len(rates) == 0:
            raise ValueError("❌ Aucune donnée reçue depuis MT5.")

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df.columns = df.columns.str.lower()
        df.reset_index(drop=True, inplace=True)

        os.makedirs(os.path.dirname(PARQUET_PATH), exist_ok=True)
        df.to_parquet(PARQUET_PATH, index=False)
        mt5.shutdown()
        logger.info(f"✅ {len(df)} barres sauvegardées dans {PARQUET_PATH}")

    # 🔹 Format final (comme yfinance)
    df = df[["time", "open", "high", "low", "close"]].dropna().reset_index(drop=True)
    
    split_date = pd.Timestamp("2024-01-01")

    # Séparer en train / test selon la date
    df_train = df[df['time'] < split_date]
    df_test = df[df['time'] >= split_date]
    return df_train, df_test
