"""
Gold Layer Service v3.0 - Load vers 4 tables séparées
Charge les .parquet transformés (Silver) dans les 4 tables
"""

from datetime import datetime
import pandas as pd

from utils.db_helper import get_db_session
from models import MT5EURUSDM15, YahooFinanceDaily, DocumentsMacro


# ============================================================================
# LOAD 1/4 - MT5
# ============================================================================

def load_mt5_to_db(mt5_parquet: str, pipeline_run_id: str = None):
    """
    Charge les features MT5 vers la table mt5_eurusd_m15

    Args:
        mt5_parquet: Chemin du fichier .parquet MT5
        pipeline_run_id: ID du run pipeline

    Returns:
        dict: Résultat avec status, rows
    """
    print(f"[GOLD/MT5] Chargement MT5 depuis {mt5_parquet}...")

    df = pd.read_parquet(mt5_parquet)

    if df.index.name == 'time':
        df = df.reset_index()

    df['time'] = pd.to_datetime(df['time'], utc=True)

    session = get_db_session()
    if not pipeline_run_id:
        pipeline_run_id = datetime.now().isoformat()

    try:
        inserted = 0
        for _, row in df.iterrows():
            record = MT5EURUSDM15(
                time=row['time'],
                open=row.get('open'),
                high=row.get('high'),
                low=row.get('low'),
                close=row.get('close'),
                tick_volume=row.get('tick_volume'),
                close_diff=row.get('close_diff'),
                close_return=row.get('close_return'),
                high_low_range=row.get('high_low_range'),
                volatility_1h=row.get('volatility_1h'),
                volatility_4h=row.get('volatility_4h'),
                momentum_15m=row.get('momentum_15m'),
                momentum_1h=row.get('momentum_1h'),
                momentum_4h=row.get('momentum_4h'),
                body=row.get('body'),
                upper_shadow=row.get('upper_shadow'),
                lower_shadow=row.get('lower_shadow'),
                pipeline_run_id=pipeline_run_id
            )
            session.merge(record)
            inserted += 1

            if inserted % 5000 == 0:
                session.commit()
                print(f"[GOLD/MT5]   {inserted} lignes...")

        session.commit()
        print(f"[GOLD/MT5] OK: {inserted} lignes chargées")

        return {
            'status': 'success',
            'table': 'mt5_eurusd_m15',
            'rows': inserted,
            'pipeline_run_id': pipeline_run_id
        }

    except Exception as e:
        session.rollback()
        print(f"[GOLD/MT5] ERREUR: {e}")
        raise
    finally:
        session.close()


# ============================================================================
# LOAD 2/4 - YAHOO FINANCE
# ============================================================================

def load_yahoo_to_db(yahoo_parquet: str, pipeline_run_id: str = None):
    """
    Charge les features Yahoo vers la table yahoo_finance_daily

    Args:
        yahoo_parquet: Chemin du fichier .parquet Yahoo
        pipeline_run_id: ID du run pipeline

    Returns:
        dict: Résultat avec status, rows
    """
    print(f"[GOLD/YAHOO] Chargement Yahoo depuis {yahoo_parquet}...")

    df = pd.read_parquet(yahoo_parquet)

    if df.index.name == 'time':
        df = df.reset_index()

    df['time'] = pd.to_datetime(df['time'], utc=True)

    session = get_db_session()
    if not pipeline_run_id:
        pipeline_run_id = datetime.now().isoformat()

    try:
        inserted = 0
        for _, row in df.iterrows():
            record = YahooFinanceDaily(
                time=row['time'],
                spx_close=row.get('spx_close'),
                spx_trend=row.get('spx_trend'),
                risk_on=row.get('risk_on'),
                gold_close=row.get('gold_close'),
                gold_trend=row.get('gold_trend'),
                safe_haven=row.get('safe_haven'),
                dxy_close=row.get('dxy_close'),
                dxy_trend_1h=row.get('dxy_trend_1h'),
                dxy_trend_4h=row.get('dxy_trend_4h'),
                dxy_strength=row.get('dxy_strength'),
                vix_close=row.get('vix_close'),
                vix_level=row.get('vix_level'),
                vix_change=row.get('vix_change'),
                market_stress=row.get('market_stress'),
                pipeline_run_id=pipeline_run_id
            )
            session.merge(record)
            inserted += 1

        session.commit()
        print(f"[GOLD/YAHOO] OK: {inserted} lignes chargées")

        return {
            'status': 'success',
            'table': 'yahoo_finance_daily',
            'rows': inserted,
            'pipeline_run_id': pipeline_run_id
        }

    except Exception as e:
        session.rollback()
        print(f"[GOLD/YAHOO] ERREUR: {e}")
        raise
    finally:
        session.close()


# ============================================================================
# LOAD 3/4 - DOCUMENTS MACRO
# ============================================================================

def load_documents_to_db(documents_parquet: str, pipeline_run_id: str = None):
    """
    Charge les documents macro vers la table documents_macro

    Args:
        documents_parquet: Chemin du fichier .parquet Documents
        pipeline_run_id: ID du run pipeline

    Returns:
        dict: Résultat avec status, rows
    """
    print(f"[GOLD/DOCS] Chargement Documents depuis {documents_parquet}...")

    df = pd.read_parquet(documents_parquet)

    if df.index.name == 'time':
        df = df.reset_index()

    df['time'] = pd.to_datetime(df['time'], utc=True)

    session = get_db_session()
    if not pipeline_run_id:
        pipeline_run_id = datetime.now().isoformat()

    try:
        inserted = 0
        for _, row in df.iterrows():
            # Conversion NaN -> None pour colonnes Float et Integer
            def safe_get(key, default=None):
                val = row.get(key, default)
                if pd.isna(val):
                    return default
                return val

            # Conversion spéciale pour Integer (NaN -> 0 ou None)
            inflation_pressure = row.get('inflation_pressure')
            if pd.isna(inflation_pressure):
                inflation_pressure = None
            else:
                inflation_pressure = int(inflation_pressure)

            record = DocumentsMacro(
                time=row['time'],
                data_type=safe_get('data_type'),
                frequency=safe_get('frequency'),
                eurozone_pib=safe_get('eurozone_pib'),
                pib_change=safe_get('pib_change'),
                pib_growth=safe_get('pib_growth'),
                eurozone_cpi=safe_get('eurozone_cpi'),
                cpi_change=safe_get('cpi_change'),
                inflation_pressure=inflation_pressure,
                event_title=safe_get('event_title'),
                event_impact=safe_get('event_impact'),
                event_impact_score=safe_get('event_impact_score'),
                pipeline_run_id=pipeline_run_id
            )
            session.merge(record)
            inserted += 1

        session.commit()
        print(f"[GOLD/DOCS] OK: {inserted} lignes chargées")

        return {
            'status': 'success',
            'table': 'documents_macro',
            'rows': inserted,
            'pipeline_run_id': pipeline_run_id
        }

    except Exception as e:
        session.rollback()
        print(f"[GOLD/DOCS] ERREUR: {e}")
        raise
    finally:
        session.close()