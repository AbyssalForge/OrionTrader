"""
Bronze Layer Service - Extraction des données brutes
Les données sont sauvegardées en fichiers .parquet
"""

import os
from datetime import datetime
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


def load_mt5_to_db(parquet_path: str):
    """
    Charge les données MT5 depuis .parquet vers la DB

    Args:
        parquet_path: Chemin du fichier .parquet

    Returns:
        dict: Résultat avec status, rows, pipeline_run_id
    """
    from utils.db_helper import get_db_session
    from models import RawMT5EURUSDM15

    print(f"[LOAD/MT5] Chargement depuis {parquet_path}...")

    # Lecture du .parquet
    df = pd.read_parquet(parquet_path)
    if 'time' not in df.columns:
        df = df.reset_index()
    df['time'] = pd.to_datetime(df['time'], utc=True)

    # Chargement en DB
    session = get_db_session()
    pipeline_run_id = datetime.now().isoformat()

    try:
        inserted = 0
        for _, row in df.iterrows():
            record = RawMT5EURUSDM15(
                time=row['time'],
                open=row.get('open'),
                high=row.get('high'),
                low=row.get('low'),
                close=row.get('close'),
                tick_volume=row.get('tick_volume'),
                spread=row.get('spread'),
                real_volume=row.get('real_volume'),
                pipeline_run_id=pipeline_run_id
            )
            session.merge(record)
            inserted += 1

        session.commit()
        print(f"[LOAD/MT5] ✅ {inserted} lignes chargées dans raw_mt5_eurusd_m15")

        return {
            "status": "success",
            "rows": inserted,
            "pipeline_run_id": pipeline_run_id
        }

    except Exception as e:
        session.rollback()
        print(f"[LOAD/MT5] ❌ Erreur: {e}")
        raise
    finally:
        session.close()


def load_stooq_to_db(parquet_paths: dict):
    """
    Charge les données Stooq depuis .parquet vers la DB

    Args:
        parquet_paths: Dictionnaire {symbole: chemin_fichier}

    Returns:
        dict: Résultat avec status, rows, pipeline_run_id
    """
    from utils.db_helper import get_db_session
    from models import RawStooqDaily

    print(f"[LOAD/STOOQ] Chargement de {len(parquet_paths)} actifs...")

    session = get_db_session()
    pipeline_run_id = datetime.now().isoformat()

    try:
        total_inserted = 0

        for symbol, path in parquet_paths.items():
            print(f"[LOAD/STOOQ] Chargement {symbol.upper()}...")
            df = pd.read_parquet(path)

            if df.index.name == 'time' or 'time' not in df.columns:
                df = df.reset_index()

            df['time'] = pd.to_datetime(df['time'], utc=True)

            for _, row in df.iterrows():
                record = RawStooqDaily(
                    time=row['time'],
                    symbol=symbol.upper(),
                    open=row.get('open') or row.get('Open'),
                    high=row.get('high') or row.get('High'),
                    low=row.get('low') or row.get('Low'),
                    close=row.get('close') or row.get('Close'),
                    volume=row.get('volume') or row.get('Volume'),
                    pipeline_run_id=pipeline_run_id
                )
                session.merge(record)
                total_inserted += 1

        session.commit()
        print(f"[LOAD/STOOQ] ✅ {total_inserted} lignes chargées dans raw_stooq_daily")

        return {
            "status": "success",
            "rows": total_inserted,
            "pipeline_run_id": pipeline_run_id
        }

    except Exception as e:
        session.rollback()
        print(f"[LOAD/STOOQ] ❌ Erreur: {e}")
        raise
    finally:
        session.close()


def load_eurostat_to_db(parquet_paths: dict):
    """
    Charge les données Eurostat depuis .parquet vers la DB

    Args:
        parquet_paths: Dictionnaire {type: chemin_fichier}

    Returns:
        dict: Résultat avec status, rows, pipeline_run_id
    """
    from utils.db_helper import get_db_session
    from models import RawEurostatMacro, RawEconomicEvents

    print(f"[LOAD/EUROSTAT] Chargement Eurostat...")

    session = get_db_session()
    pipeline_run_id = datetime.now().isoformat()

    try:
        total_inserted = 0

        # PIB
        if 'pib' in parquet_paths:
            df_pib = pd.read_parquet(parquet_paths["pib"])
            if df_pib.index.name in ['TIME_PERIOD', 'time']:
                df_pib = df_pib.reset_index()
            df_pib['time'] = pd.to_datetime(df_pib.iloc[:, 0], utc=True)

            for _, row in df_pib.iterrows():
                record = RawEurostatMacro(
                    time=row['time'],
                    indicator='PIB',
                    value=row.get('eurozone_pib'),
                    unit='INDEX',
                    pipeline_run_id=pipeline_run_id
                )
                session.merge(record)
                total_inserted += 1

        # CPI
        if 'cpi' in parquet_paths:
            df_cpi = pd.read_parquet(parquet_paths["cpi"])
            if df_cpi.index.name in ['TIME_PERIOD', 'time']:
                df_cpi = df_cpi.reset_index()
            df_cpi['time'] = pd.to_datetime(df_cpi.iloc[:, 0], utc=True)

            for _, row in df_cpi.iterrows():
                record = RawEurostatMacro(
                    time=row['time'],
                    indicator='CPI',
                    value=row.get('eurozone_cpi'),
                    unit='INDEX',
                    pipeline_run_id=pipeline_run_id
                )
                session.merge(record)
                total_inserted += 1

        # Economic Events
        if 'events' in parquet_paths:
            df_events = pd.read_parquet(parquet_paths["events"])
            df_events['time'] = pd.to_datetime(df_events['time'], utc=True)

            for _, row in df_events.iterrows():
                record = RawEconomicEvents(
                    time=row['time'],
                    title=row['title'],
                    impact=row.get('impact'),
                    country='EU',
                    currency='EUR',
                    pipeline_run_id=pipeline_run_id
                )
                session.merge(record)
                total_inserted += 1

        session.commit()
        print(f"[LOAD/EUROSTAT] ✅ {total_inserted} lignes chargées")

        return {
            "status": "success",
            "rows": total_inserted,
            "pipeline_run_id": pipeline_run_id
        }

    except Exception as e:
        session.rollback()
        print(f"[LOAD/EUROSTAT] ❌ Erreur: {e}")
        raise
    finally:
        session.close()
