import sys
import pandas as pd
import os
import time

from clients.vault_helper import get_vault
from clients.mt5_client import MT5Client, MT5Timeframe

vault = get_vault()

SYMBOL = "EURUSD"
TIMEFRAME = MT5Timeframe.M15  # Utiliser notre classe de timeframes
START = pd.Timestamp("2023-01-01")
END = pd.Timestamp("2025-11-01")
PARQUET_PATH = f"data/{SYMBOL.lower()}_{TIMEFRAME}.parquet"

# Récupérer les credentials depuis les variables d'environnement
MT5_LOGIN = int(vault.get_secret('MetaTrader', 'MT5_LOGIN'))
MT5_PASSWORD = vault.get_secret('MetaTrader', 'MT5_PASSWORD')
MT5_SERVER = vault.get_secret('MetaTrader', 'MT5_SERVER')

def connect_mt5(max_retries=3, wait_time=2):
    """Connexion robuste à MetaTrader 5 via RPyC"""

    for attempt in range(1, max_retries + 1):

        try:
            # Créer une instance du client
            mt5_client = MT5Client(host=MT5_HOST, port=MT5_PORT)
            mt5_client.connect()

            # Initialiser avec les credentials si fournis
            if MT5_LOGIN and MT5_PASSWORD and MT5_SERVER:
                success = mt5_client.initialize(
                    login=int(MT5_LOGIN),
                    password=MT5_PASSWORD,
                    server=MT5_SERVER
                )

                if not success:
                    err = mt5_client.last_error()
                    mt5_client.disconnect()
                    time.sleep(wait_time)
                    continue
            else:
                # Initialiser sans credentials (utilise le compte déjà connecté dans MT5)
                mt5_client.initialize()

            return mt5_client

        except Exception as e:
            time.sleep(wait_time)
            continue

    return None


def import_data():
    """
    Télécharge les données depuis MT5 ou charge depuis cache local.
    Retourne un DataFrame avec colonnes open, high, low, close.
    """

    # 🔹 Si fichier existant → on le réutilise
    if os.path.exists(PARQUET_PATH):
        df = pd.read_parquet(PARQUET_PATH)

    else:
        mt5_client = connect_mt5()

        if not mt5_client:
            raise RuntimeError("Impossible de se connecter à MetaTrader 5.")

        try:
            # Utiliser copy_rates_range avec notre client
            rates = mt5_client.copy_rates_range(
                symbol=SYMBOL,
                timeframe=TIMEFRAME,
                date_from=START.to_pydatetime(),
                date_to=END.to_pydatetime()
            )

            if rates is None or len(rates) == 0:
                raise ValueError("❌ Aucune donnée reçue depuis MT5.")

            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            df.columns = df.columns.str.lower()
            df.reset_index(drop=True, inplace=True)

            os.makedirs(os.path.dirname(PARQUET_PATH), exist_ok=True)
            df.to_parquet(PARQUET_PATH, index=False)

        finally:
            # Toujours fermer la connexion
            mt5_client.disconnect()

    # 🔹 Format final (comme yfinance)
    df = df[["time", "open", "high", "low", "close"]].dropna().reset_index(drop=True)

    split_date = pd.Timestamp("2024-01-01")

    # Séparer en train / test selon la date
    df_train = df[df['time'] < split_date]
    df_test = df[df['time'] >= split_date]
    return df_train, df_test
