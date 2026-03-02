"""
Router Data - Endpoints pour features et données d'entraînement ML
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List, Optional
from datetime import datetime

from models import MT5EURUSDM15, YahooFinanceDaily, DocumentsMacro, MarketSnapshotM15

from app.core.dependencies import get_db
from app.core.auth import verify_api_token
from app.models.api_token import APIToken
from app.schemas.data import (
    YahooFinanceResponse,
    DocumentsMacroResponse,
    TrainingDataResponse
)
from app.schemas.market import MT5Response

router = APIRouter()



@router.get("/features/mt5", response_model=List[MT5Response])
def get_mt5_features(
    start_date: Optional[datetime] = Query(None, description="Date de début"),
    end_date: Optional[datetime] = Query(None, description="Date de fin"),
    limit: int = Query(1000, ge=1, le=100000, description="Nombre max de résultats"),
    offset: int = Query(0, ge=0, description="Offset pour pagination"),
    db: Session = Depends(get_db),
    token: APIToken = Depends(verify_api_token)
):
    """
    Features microstructure MT5 (M15)

    Récupère les features haute fréquence pour ML:
    - Prix OHLCV
    - Volatilité multi-horizon (1h, 4h)
    - Momentum multi-horizon (15m, 1h, 4h)
    - Patterns de chandeliers (body, shadows)
    - Returns et ranges

    **Use case:** Entraînement modèles ML, feature engineering

    **Fréquence:** 15 minutes (M15)
    **Volume:** ~96 bars/jour, ~670 bars/semaine
    """
    query = db.query(MT5EURUSDM15)

    if start_date:
        query = query.filter(MT5EURUSDM15.time >= start_date)
    if end_date:
        query = query.filter(MT5EURUSDM15.time <= end_date)

    query = query.order_by(desc(MT5EURUSDM15.time))
    results = query.offset(offset).limit(limit).all()

    if not results:
        raise HTTPException(status_code=404, detail="Aucune donnée MT5 trouvée")

    return results



@router.get("/features/yahoo", response_model=List[YahooFinanceResponse])
def get_yahoo_features(
    start_date: Optional[datetime] = Query(None, description="Date de début"),
    end_date: Optional[datetime] = Query(None, description="Date de fin"),
    limit: int = Query(1000, ge=1, le=10000, description="Nombre max de résultats"),
    offset: int = Query(0, ge=0, description="Offset pour pagination"),
    db: Session = Depends(get_db),
    token: APIToken = Depends(verify_api_token)
):
    """
    Features macro-financières Yahoo Finance (Daily)

    Récupère les features macro pour ML:
    - EUR/USD spot price
    - DXY (US Dollar Index)
    - Yields (EUR, US, spread)
    - VIX (volatilité)
    - Risk sentiment

    **Use case:** Analyse fondamentale, features macro pour ML

    **Fréquence:** Daily
    **Volume:** ~7 bars/semaine, ~30 bars/mois
    """
    query = db.query(YahooFinanceDaily)

    if start_date:
        query = query.filter(YahooFinanceDaily.time >= start_date)
    if end_date:
        query = query.filter(YahooFinanceDaily.time <= end_date)

    query = query.order_by(desc(YahooFinanceDaily.time))
    results = query.offset(offset).limit(limit).all()

    if not results:
        raise HTTPException(status_code=404, detail="Aucune donnée Yahoo trouvée")

    return results



@router.get("/features/macro", response_model=List[DocumentsMacroResponse])
def get_macro_features(
    start_date: Optional[datetime] = Query(None, description="Date de début"),
    end_date: Optional[datetime] = Query(None, description="Date de fin"),
    limit: int = Query(1000, ge=1, le=10000, description="Nombre max de résultats"),
    offset: int = Query(0, ge=0, description="Offset pour pagination"),
    db: Session = Depends(get_db),
    token: APIToken = Depends(verify_api_token)
):
    """
    Features macro-économiques (Documents)

    Récupère les indicateurs économiques pour ML:
    - PIB (EUR, US, différentiel)
    - Inflation (EUR, US, différentiel)
    - Taux directeurs (ECB, FED, spread)
    - Balances commerciales
    - Chômage

    **Use case:** Analyse fondamentale macro, stratégies long-terme

    **Fréquence:** Monthly/Quarterly/Annual (variable selon indicateur)
    **Volume:** ~12-50 bars/an selon indicateur
    """
    query = db.query(DocumentsMacro)

    if start_date:
        query = query.filter(DocumentsMacro.time >= start_date)
    if end_date:
        query = query.filter(DocumentsMacro.time <= end_date)

    query = query.order_by(desc(DocumentsMacro.time))
    results = query.offset(offset).limit(limit).all()

    if not results:
        raise HTTPException(status_code=404, detail="Aucune donnée macro trouvée")

    return results



@router.get("/training", response_model=List[TrainingDataResponse])
def get_training_data(
    start_date: Optional[datetime] = Query(None, description="Date de début"),
    end_date: Optional[datetime] = Query(None, description="Date de fin"),
    limit: int = Query(1000, ge=1, le=100000, description="Nombre max de résultats"),
    offset: int = Query(0, ge=0, description="Offset pour pagination"),
    db: Session = Depends(get_db),
    token: APIToken = Depends(verify_api_token)
):
    """
    Dataset complet pour entraînement ML

    Récupère les données complètes avec JOINs automatiques:
    - MT5 features (microstructure)
    - Yahoo features (macro-financier)
    - Macro features (économie)
    - Snapshot features (composites)

    **Use case:** Entraînement modèles ML, backtesting complet

    Cette requête effectue les JOINs automatiquement via les foreign keys
    du Market Snapshot, offrant un dataset prêt à l'emploi.

    **Fréquence:** M15 (aligné sur MT5)
    **Colonnes:** ~40 features combinées

    **Exemple:**
    - Dernières 1000 bars: `?limit=1000`
    - Dernière semaine: `?start_date=2026-01-06T00:00:00&limit=672`
    - Période spécifique: `?start_date=2025-01-01&end_date=2025-12-31&limit=35000`
    """
    query = db.query(
        MarketSnapshotM15.time,

        MT5EURUSDM15.open.label('mt5_open'),
        MT5EURUSDM15.high.label('mt5_high'),
        MT5EURUSDM15.low.label('mt5_low'),
        MT5EURUSDM15.close.label('mt5_close'),
        MT5EURUSDM15.tick_volume.label('mt5_tick_volume'),

        MT5EURUSDM15.close_return,
        MT5EURUSDM15.volatility_1h,
        MT5EURUSDM15.volatility_4h,
        MT5EURUSDM15.momentum_15m,
        MT5EURUSDM15.momentum_1h,
        MT5EURUSDM15.momentum_4h,

        YahooFinanceDaily.eurusd_close,
        YahooFinanceDaily.dxy_close,
        YahooFinanceDaily.vix_close,
        YahooFinanceDaily.yield_spread_eur_us,
        YahooFinanceDaily.risk_sentiment,

        DocumentsMacro.eur_gdp_growth,
        DocumentsMacro.us_gdp_growth,
        DocumentsMacro.eur_inflation_rate,
        DocumentsMacro.us_inflation_rate,
        DocumentsMacro.ecb_rate,
        DocumentsMacro.fed_rate,

        MarketSnapshotM15.macro_micro_aligned,
        MarketSnapshotM15.euro_strength_bias,
        MarketSnapshotM15.regime_composite,
        MarketSnapshotM15.volatility_regime,
        MarketSnapshotM15.signal_confidence_score,
        MarketSnapshotM15.trend_strength_composite
    ).join(
        MT5EURUSDM15,
        MarketSnapshotM15.mt5_time == MT5EURUSDM15.time
    ).outerjoin(
        YahooFinanceDaily,
        MarketSnapshotM15.yahoo_time == YahooFinanceDaily.time
    ).outerjoin(
        DocumentsMacro,
        MarketSnapshotM15.docs_time == DocumentsMacro.time
    )

    if start_date:
        query = query.filter(MarketSnapshotM15.time >= start_date)
    if end_date:
        query = query.filter(MarketSnapshotM15.time <= end_date)

    query = query.order_by(desc(MarketSnapshotM15.time))
    results = query.offset(offset).limit(limit).all()

    if not results:
        raise HTTPException(status_code=404, detail="Aucune donnée d'entraînement trouvée")

    training_data = []
    for row in results:
        training_data.append(TrainingDataResponse(
            time=row.time,
            mt5_open=row.mt5_open,
            mt5_high=row.mt5_high,
            mt5_low=row.mt5_low,
            mt5_close=row.mt5_close,
            mt5_tick_volume=row.mt5_tick_volume,
            close_return=row.close_return,
            volatility_1h=row.volatility_1h,
            volatility_4h=row.volatility_4h,
            momentum_15m=row.momentum_15m,
            momentum_1h=row.momentum_1h,
            momentum_4h=row.momentum_4h,
            eurusd_close=row.eurusd_close,
            dxy_close=row.dxy_close,
            vix_close=row.vix_close,
            yield_spread_eur_us=row.yield_spread_eur_us,
            risk_sentiment=row.risk_sentiment,
            eur_gdp_growth=row.eur_gdp_growth,
            us_gdp_growth=row.us_gdp_growth,
            eur_inflation_rate=row.eur_inflation_rate,
            us_inflation_rate=row.us_inflation_rate,
            ecb_rate=row.ecb_rate,
            fed_rate=row.fed_rate,
            macro_micro_aligned=row.macro_micro_aligned,
            euro_strength_bias=row.euro_strength_bias,
            regime_composite=row.regime_composite,
            volatility_regime=row.volatility_regime,
            signal_confidence_score=row.signal_confidence_score,
            trend_strength_composite=row.trend_strength_composite
        ))

    return training_data



@router.get("/stats")
def get_data_stats(
    db: Session = Depends(get_db),
    token: APIToken = Depends(verify_api_token)
):
    """
    Statistiques des données disponibles

    Retourne un résumé de toutes les tables:
    - Nombre total de lignes
    - Période couverte (première et dernière date)
    - Dernier pipeline_run_id

    **Use case:** Monitoring de la qualité des données, health check
    """
    stats = {}

    mt5_count = db.query(MT5EURUSDM15).count()
    mt5_first = db.query(MT5EURUSDM15).order_by(MT5EURUSDM15.time).first()
    mt5_last = db.query(MT5EURUSDM15).order_by(desc(MT5EURUSDM15.time)).first()

    stats['mt5_eurusd_m15'] = {
        'total_rows': mt5_count,
        'first_date': mt5_first.time if mt5_first else None,
        'last_date': mt5_last.time if mt5_last else None,
        'last_pipeline_run': mt5_last.pipeline_run_id if mt5_last else None
    }

    yahoo_count = db.query(YahooFinanceDaily).count()
    yahoo_first = db.query(YahooFinanceDaily).order_by(YahooFinanceDaily.time).first()
    yahoo_last = db.query(YahooFinanceDaily).order_by(desc(YahooFinanceDaily.time)).first()

    stats['yahoo_finance_daily'] = {
        'total_rows': yahoo_count,
        'first_date': yahoo_first.time if yahoo_first else None,
        'last_date': yahoo_last.time if yahoo_last else None,
        'last_pipeline_run': yahoo_last.pipeline_run_id if yahoo_last else None
    }

    docs_count = db.query(DocumentsMacro).count()
    docs_first = db.query(DocumentsMacro).order_by(DocumentsMacro.time).first()
    docs_last = db.query(DocumentsMacro).order_by(desc(DocumentsMacro.time)).first()

    stats['documents_macro'] = {
        'total_rows': docs_count,
        'first_date': docs_first.time if docs_first else None,
        'last_date': docs_last.time if docs_last else None,
        'last_pipeline_run': docs_last.pipeline_run_id if docs_last else None
    }

    snapshot_count = db.query(MarketSnapshotM15).count()
    snapshot_first = db.query(MarketSnapshotM15).order_by(MarketSnapshotM15.time).first()
    snapshot_last = db.query(MarketSnapshotM15).order_by(desc(MarketSnapshotM15.time)).first()

    stats['market_snapshot_m15'] = {
        'total_rows': snapshot_count,
        'first_date': snapshot_first.time if snapshot_first else None,
        'last_date': snapshot_last.time if snapshot_last else None,
        'last_pipeline_run': snapshot_last.pipeline_run_id if snapshot_last else None
    }

    return stats



@router.get("/features/latest")
def get_latest_features(
    db: Session = Depends(get_db),
    token: APIToken = Depends(verify_api_token)
):
    """
    Dernières features disponibles par source

    Récupère la dernière ligne de chaque table:
    - MT5 (microstructure)
    - Yahoo (macro-financier)
    - Documents (économie)

    **Use case:** Quick check de la fraîcheur des données
    """
    mt5 = db.query(MT5EURUSDM15).order_by(desc(MT5EURUSDM15.time)).first()

    yahoo = db.query(YahooFinanceDaily).order_by(desc(YahooFinanceDaily.time)).first()

    docs = db.query(DocumentsMacro).order_by(desc(DocumentsMacro.time)).first()

    return {
        "mt5": MT5Response.model_validate(mt5) if mt5 else None,
        "yahoo": YahooFinanceResponse.model_validate(yahoo) if yahoo else None,
        "documents": DocumentsMacroResponse.model_validate(docs) if docs else None
    }
