"""
Bronze Layer Service - Extraction des données brutes
Les données sont sauvegardées en fichiers .parquet

Utilise les clients modulaires pour interagir avec les sources de données:
- MT5Client pour MetaTrader5
- YahooFinanceClient pour Yahoo Finance
- EurostatClient pour les sources économiques
"""

import os
import pandas as pd

from clients.yahoo_client import YahooFinanceClient
from clients.eurostat_client import EurostatClient
from utils.mt5_server import import_data

def extract_mt5_data(start, end):
    """
    Extrait les données MT5 et les sauvegarde en .parquet

    Args:
        start: Date de début
        end: Date de fin

    Returns:
        str: Chemin du fichier .parquet
    """
    base_path = "data/mt5"
    os.makedirs(base_path, exist_ok=True)

    print(f"[BRONZE/MT5] Extraction MT5: {start} -> {end}")

    # Extraction
    df = pd.DataFrame.from_dict(import_data(start=start, end=end))
    print(f"[BRONZE/MT5] OK: {len(df)} lignes extraites")

    # Sauvegarde en .parquet
    path = f"{base_path}/eurusd_mt5.parquet"
    df.to_parquet(path)
    print(f"[BRONZE/MT5] OK: Donnees sauvegardees: {path}")

    return path


def extract_yahoo_data(start=None, end=None):
    """
    Extrait les données Yahoo Finance et les sauvegarde en .parquet

    MODIFIÉ: Utilise YahooFinanceClient avec Vault
    Avantages: DXY et VIX maintenant disponibles (9/9 actifs vs 7/9 avec Stooq)

    Args:
        start: Date de début (datetime). Par défaut: 1 an avant end
        end: Date de fin (datetime). Par défaut: maintenant

    Returns:
        dict: Dictionnaire {symbole: chemin_fichier}
    """
    base_path = "data/api"
    os.makedirs(base_path, exist_ok=True)

    print("[BRONZE/YAHOO] Extraction Yahoo Finance via Client...")

    # Utiliser le client Yahoo Finance (avec Vault)
    yahoo_client = YahooFinanceClient(use_vault=True)
    macro_context = yahoo_client.get_macro_context(start=start, end=end)
    print(f"[BRONZE/YAHOO] OK: {len(macro_context)} actifs extraits")

    # Sauvegarde en .parquet
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

    total_rows = 0
    for key, name in asset_mapping.items():
        if key in macro_context:
            df = macro_context[key]
            num_rows = len(df)
            total_rows += num_rows

            # Afficher les dates min/max pour debug
            date_min = df.index.min()
            date_max = df.index.max()
            print(f"[BRONZE/YAHOO] {name}: {num_rows} lignes (de {date_min.date()} à {date_max.date()})")

            file_path = f"{base_path}/{key}_daily.parquet"
            df.to_parquet(file_path)
            paths[key] = file_path
        else:
            print(f"[BRONZE/YAHOO] ATTENTION: {name} non disponible, ignore")

    print(f"[BRONZE/YAHOO] Total lignes toutes sources: {total_rows}")

    print(f"[BRONZE/YAHOO] OK: {len(paths)} actifs sauvegardes")

    return paths


def extract_eurostat_data(start=None):
    """
    Extrait les données économiques et les sauvegarde en .parquet

    MODIFIÉ: Utilise EurostatClient avec Vault
    Sources: OECD + World Bank + ECB + Investing.com
    Avantages: PIB et CPI à jour, pas de problème de période temporelle

    Args:
        start: Date de début (datetime). Par défaut: varie selon la source (2015-2020)

    Returns:
        dict: Dictionnaire {type: chemin_fichier} (pib, cpi, events)
    """
    base_path = "data/documents"
    os.makedirs(base_path, exist_ok=True)

    print("[BRONZE/DOCUMENTS] Extraction documents economiques via Client...")

    # Utiliser le client Eurostat (avec Vault)
    eurostat_client = EurostatClient(use_vault=True)
    documents = eurostat_client.extract_all_documents(start=start)

    # Sauvegarder les DataFrames en parquet
    paths = {}
    for key, df in documents.items():
        if df is not None and not df.empty:
            file_path = f"{base_path}/{key}.parquet"
            df.to_parquet(file_path)
            paths[key] = file_path
            print(f"[BRONZE/DOCUMENTS] Sauvegarde {key}: {file_path}")

    print(f"[BRONZE/DOCUMENTS] OK: {len(paths)} documents sauvegardes")
    print(f"[BRONZE/DOCUMENTS]   - PIB: {paths.get('pib')}")
    print(f"[BRONZE/DOCUMENTS]   - CPI: {paths.get('cpi')}")
    print(f"[BRONZE/DOCUMENTS]   - Events: {paths.get('events')}")

    return paths
