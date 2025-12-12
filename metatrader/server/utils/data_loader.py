import MetaTrader5 as mt5
import pandas as pd
import os
import time
from .vault_helper import get_vault

vault = get_vault()

SYMBOL = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_M15
START = pd.Timestamp("2023-01-01")
END = pd.Timestamp("2025-11-01")
PARQUET_PATH = f"data/{SYMBOL.lower()}_{TIMEFRAME}.parquet"

MT5_LOGIN = int(vault.get_secret('MetaTrader', 'MT5_LOGIN'))
MT5_PASSWORD = vault.get_secret('MetaTrader', 'MT5_PASSWORD')
MT5_SERVER = vault.get_secret('MetaTrader', 'MT5_SERVER')


def connect_mt5(max_retries=3, wait_time=2):
    """Connexion robuste à MetaTrader 5"""
    
    print(f"MT5_LOGIN: {MT5_LOGIN}")
    print(f"MT5_PASSWORD: {MT5_PASSWORD}")
    print(f"MT5_SERVER: {MT5_SERVER}")
    
    time.sleep(1)

    for attempt in range(1, max_retries + 1):
        if not mt5.initialize():
            err = mt5.last_error()
            print("MT5 init failed:", mt5.last_error())
            time.sleep(wait_time)
            continue

        if MT5_LOGIN:
            if not mt5.login(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
                err = mt5.last_error()
                mt5.shutdown()
                print("MT5 init login failed:", mt5.last_error())
                time.sleep(wait_time)
                continue

        return True

    return False


def import_data():
    """
    Télécharge les données depuis MT5 ou charge depuis cache local.
    Retourne un DataFrame avec colonnes open, high, low, close.
    """

    # 🔹 Si fichier existant → on le réutilise
    if os.path.exists(PARQUET_PATH):
        df = pd.read_parquet(PARQUET_PATH)

    else:
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

    # 🔹 Format final (comme yfinance)
    df = df.dropna().reset_index(drop=True)
    
    split_date = pd.Timestamp("2024-01-01")

    return df
