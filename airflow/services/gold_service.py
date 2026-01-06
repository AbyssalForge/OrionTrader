"""
Gold Layer Service - Load des features dans la base de données
Charge le .parquet transformé (Silver) dans la table features_eurusd_m15
"""

from datetime import datetime
import pandas as pd

from utils.db_helper import get_db_session
from models import FeaturesEURUSDM15


def load_features_to_db(features_parquet: str):
    """
    Charge les features depuis .parquet vers la DB

    Args:
        features_parquet: Chemin du fichier .parquet avec features

    Returns:
        dict: Résultat avec status, rows, pipeline_run_id
    """
    print(f"[GOLD/LOAD] Chargement features depuis {features_parquet}...")

    # Lecture du .parquet
    df = pd.read_parquet(features_parquet)

    if df.index.name == 'time':
        df = df.reset_index()

    df['time'] = pd.to_datetime(df['time'], utc=True)

    # Chargement en DB
    session = get_db_session()
    pipeline_run_id = datetime.now().isoformat()

    try:
        inserted = 0
        for _, row in df.iterrows():
            record = FeaturesEURUSDM15(
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
                dxy_close=row.get('dxy_close'),
                dxy_trend_1h=row.get('dxy_trend_1h'),
                dxy_trend_4h=row.get('dxy_trend_4h'),
                dxy_strength=row.get('dxy_strength'),
                vix_close=row.get('vix_close'),
                vix_level=row.get('vix_level'),
                vix_change=row.get('vix_change'),
                market_stress=int(row.get('market_stress', 0)),
                spx_close=row.get('spx_close'),
                spx_trend=row.get('spx_trend'),
                risk_on=int(row.get('risk_on', 0)),
                gold_close=row.get('gold_close'),
                gold_trend=row.get('gold_trend'),
                safe_haven=int(row.get('safe_haven', 0)),
                eurozone_pib=row.get('eurozone_pib'),
                pib_change=row.get('pib_change'),
                pib_growth=int(row.get('pib_growth', 0)),
                eurozone_cpi=row.get('eurozone_cpi'),
                cpi_change=row.get('cpi_change'),
                inflation_pressure=int(row.get('inflation_pressure', 0)),
                event_title=str(row.get('event_title', ''))[:200],
                event_impact=str(row.get('event_impact', ''))[:10],
                event_impact_score=int(row.get('event_impact_score', 0)),
                macro_micro_aligned=int(row.get('macro_micro_aligned', 0)),
                euro_strength_bias=int(row.get('euro_strength_bias', 0)),
                pipeline_run_id=pipeline_run_id
            )
            session.merge(record)
            inserted += 1

        session.commit()
        print(f"[GOLD/LOAD] ✅ {inserted} lignes chargées dans features_eurusd_m15")

        return {
            "status": "success",
            "rows": inserted,
            "pipeline_run_id": pipeline_run_id
        }

    except Exception as e:
        session.rollback()
        print(f"[GOLD/LOAD] ❌ Erreur: {e}")
        raise
    finally:
        session.close()


def create_ml_dataset(load_result: dict):
    """
    Crée les datasets ML depuis les features (TODO)

    Args:
        load_result: Résultat du chargement des features

    Returns:
        dict: Résultat avec status et message
    """
    print("[GOLD/ML] Création ML datasets...")
    print(f"[GOLD/ML] Features disponibles: {load_result['rows']} lignes")

    # TODO: Implémenter la création des labels et datasets ML
    # - Classification: Buy/Sell/Hold
    # - Regression: Future returns
    # - RL: State/Action/Reward

    return {"status": "pending", "message": "À implémenter"}
