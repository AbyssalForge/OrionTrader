"""
Bronze Layer Service - Extraction des données brutes
Les données sont sauvegardées en fichiers .parquet
"""

import os
import pandas as pd

from utils.mt5_server import import_data
from utils.apis_helper import get_macro_context_yahoo
from utils.documents_helper import extract_documents_alternative

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


def extract_stooq_data():
    """
    Extrait les données Yahoo Finance et les sauvegarde en .parquet

    MODIFIÉ: Utilise Yahoo Finance au lieu de Stooq
    Avantages: DXY et VIX maintenant disponibles (9/9 actifs vs 7/9 avec Stooq)

    Returns:
        dict: Dictionnaire {symbole: chemin_fichier}
    """
    base_path = "data/api"
    os.makedirs(base_path, exist_ok=True)

    print("[BRONZE/YAHOO] Extraction Yahoo Finance...")

    # Extraction via Yahoo Finance (MEILLEUR que Stooq!)
    macro_context = get_macro_context_yahoo(days=365)
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

    for key, name in asset_mapping.items():
        if key in macro_context:
            print(f"[BRONZE/YAHOO] Sauvegarde {name}...")
            file_path = f"{base_path}/{key}_daily.parquet"
            macro_context[key].to_parquet(file_path)
            paths[key] = file_path
        else:
            print(f"[BRONZE/YAHOO] ATTENTION: {name} non disponible, ignore")

    print(f"[BRONZE/YAHOO] OK: {len(paths)} actifs sauvegardes")

    return paths


def extract_eurostat_data():
    """
    Extrait les données économiques et les sauvegarde en .parquet

    MODIFIÉ: Utilise OECD + World Bank + Investing.com au lieu d'Eurostat
    Avantages: PIB et CPI à jour, pas de problème de période temporelle

    Returns:
        dict: Dictionnaire {type: chemin_fichier} (pib, cpi, events)
    """
    print("[BRONZE/DOCUMENTS] Extraction documents economiques...")

    # Extraction depuis sources alternatives (OECD, World Bank, etc.)
    paths = extract_documents_alternative()

    print(f"[BRONZE/DOCUMENTS] OK: {len(paths)} documents sauvegardes")
    print(f"[BRONZE/DOCUMENTS]   - PIB: {paths.get('pib')}")
    print(f"[BRONZE/DOCUMENTS]   - CPI: {paths.get('cpi')}")
    print(f"[BRONZE/DOCUMENTS]   - Events: {paths.get('events')}")

    return paths
