"""
Bronze Layer Service - Extraction des données brutes
Les données sont sauvegardées en fichiers .parquet
"""

import os
import pandas as pd

from utils.mt5_server import import_data
from utils.alpha_vantage import get_macro_context_stooq
from utils.document_helper import extract_documents

from models import create_all_tables
from utils.db_helper import get_db_engine


def initialize_database():
    """Crée toutes les tables dans la base de données"""
    print("[INIT] Initialisation base de données...")
    engine = get_db_engine()
    create_all_tables(engine)
    print("[INIT] ✅ Tables créées")
    return {"status": "success"}


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

    print(f"[BRONZE/MT5] Extraction MT5: {start} → {end}")

    # Extraction
    df = pd.DataFrame.from_dict(import_data(start=start, end=end))
    print(f"[BRONZE/MT5] ✓ {len(df)} lignes extraites")

    # Sauvegarde en .parquet
    path = f"{base_path}/eurusd_mt5.parquet"
    df.to_parquet(path)
    print(f"[BRONZE/MT5] ✅ Données sauvegardées: {path}")

    return path


def extract_stooq_data():
    """
    Extrait les données Stooq et les sauvegarde en .parquet

    Returns:
        dict: Dictionnaire {symbole: chemin_fichier}
    """
    base_path = "data/api"
    os.makedirs(base_path, exist_ok=True)

    print("[BRONZE/STOOQ] Extraction Stooq...")

    # Extraction
    macro_context = get_macro_context_stooq(days=365)
    print(f"[BRONZE/STOOQ] ✓ {len(macro_context)} actifs extraits")

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
            print(f"[BRONZE/STOOQ] Sauvegarde {name}...")
            file_path = f"{base_path}/{key}_daily.parquet"
            macro_context[key].to_parquet(file_path)
            paths[key] = file_path
        else:
            print(f"[BRONZE/STOOQ] ⚠ {name} non disponible, ignoré")

    print(f"[BRONZE/STOOQ] ✅ {len(paths)} actifs sauvegardés")

    return paths


def extract_eurostat_data():
    """
    Extrait les données Eurostat et les sauvegarde en .parquet

    Returns:
        dict: Dictionnaire {type: chemin_fichier} (pib, cpi, events)
    """
    print("[BRONZE/EUROSTAT] Extraction Eurostat...")

    # Extraction (extract_documents sauvegarde déjà en .parquet)
    paths = extract_documents()

    print(f"[BRONZE/EUROSTAT] ✅ {len(paths)} documents sauvegardés")
    print(f"[BRONZE/EUROSTAT]   - PIB: {paths.get('pib')}")
    print(f"[BRONZE/EUROSTAT]   - CPI: {paths.get('cpi')}")
    print(f"[BRONZE/EUROSTAT]   - Events: {paths.get('events')}")

    return paths
