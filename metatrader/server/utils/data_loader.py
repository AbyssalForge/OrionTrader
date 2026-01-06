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

    # Vérifier que MT5 est installé
    if not mt5.initialize():
        terminal_info = mt5.terminal_info()
        if terminal_info is None:
            print("❌ ERREUR CRITIQUE: MetaTrader 5 n'est pas lancé ou installé!")
            print("   Solutions:")
            print("   1. Lancez MetaTrader 5 manuellement sur votre machine Windows")
            print("   2. Assurez-vous que MT5 reste ouvert pendant l'exécution")
            return False
        mt5.shutdown()

    time.sleep(1)

    for attempt in range(1, max_retries + 1):
        print(f"Tentative {attempt}/{max_retries} de connexion à MT5...")

        if not mt5.initialize():
            err = mt5.last_error()
            print(f"MT5 initialize() failed: {err}")
            print(f"  Code: {err[0]}, Message: {err[1]}")

            if err[0] == -6:
                print("  → Le terminal MT5 n'est pas ouvert ou a refusé l'autorisation")
                print("  → Vérifiez que MetaTrader 5 est lancé sur Windows")

            time.sleep(wait_time)
            continue

        if MT5_LOGIN:
            if not mt5.login(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
                err = mt5.last_error()
                mt5.shutdown()
                print(f"MT5 login() failed: {err}")
                print(f"  Code: {err[0]}, Message: {err[1]}")

                if err[0] == -6:
                    print("  → Échec d'autorisation: vérifiez les identifiants")
                    print(f"  → Login: {MT5_LOGIN}")
                    print(f"  → Server: {MT5_SERVER}")
                    print(f"  → Password: {'*' * len(MT5_PASSWORD)}")

                time.sleep(wait_time)
                continue

        print("✅ Connexion à MT5 réussie!")
        return True

    print(f"❌ Échec après {max_retries} tentatives")
    return False


def import_data(start=None, end=None, symbol=None):
    """
    Télécharge les données depuis MT5 pour une période donnée.
    Ne charge PLUS depuis cache - toujours des données fraîches.

    Args:
        start: Date de début (Timestamp ou None pour valeur par défaut)
        end: Date de fin (Timestamp ou None pour valeur par défaut)
        symbol: Symbole à récupérer (str ou None pour EURUSD)

    Returns:
        DataFrame avec colonnes open, high, low, close, time
    """
    # Valeurs par défaut
    if start is None:
        start = START
    if end is None:
        end = END
    if symbol is None:
        symbol = SYMBOL

    # Connexion à MT5
    if not connect_mt5():
        raise RuntimeError("Impossible de se connecter à MetaTrader 5.")

    print(f"📊 Récupération données MT5: {symbol} de {start} à {end}")

    # Récupération des données
    rates = mt5.copy_rates_range(symbol, TIMEFRAME, start.to_pydatetime(), end.to_pydatetime())

    if rates is None or len(rates) == 0:
        mt5.shutdown()
        raise ValueError(f"❌ Aucune donnée reçue depuis MT5 pour {symbol} ({start} - {end}).")

    # Formatage
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.columns = df.columns.str.lower()
    df = df.dropna().reset_index(drop=True)

    mt5.shutdown()

    print(f"✅ {len(df)} lignes récupérées")

    return df
