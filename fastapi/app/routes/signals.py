"""
Router Signals - Endpoints pour signaux de trading et opportunités
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from typing import List, Optional
from datetime import datetime

from models import MT5EURUSDM15, MarketSnapshotM15

from app.core.dependencies import get_db
from app.core.auth import verify_api_token
from app.models.api_token import APIToken
from app.schemas.signals import HighConfidenceSignalResponse

router = APIRouter()



@router.get("/high-confidence", response_model=List[HighConfidenceSignalResponse])
def get_high_confidence_signals(
    min_confidence: float = Query(0.7, ge=0.0, le=1.0, description="Score de confiance minimum"),
    regime: Optional[str] = Query(None, description="Filtrer par régime: risk_on, risk_off, neutral, volatile"),
    volatility_regime: Optional[str] = Query(None, description="Filtrer par volatilité: low, normal, high"),
    max_divergence: int = Query(1, ge=0, le=3, description="Divergences max tolérées"),
    start_date: Optional[datetime] = Query(None, description="Date de début"),
    end_date: Optional[datetime] = Query(None, description="Date de fin"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre max de résultats"),
    offset: int = Query(0, ge=0, description="Offset pour pagination"),
    db: Session = Depends(get_db),
    token: APIToken = Depends(verify_api_token)
):
    """
    Signaux de trading haute confiance

    Récupère les signaux avec score de confiance élevé et faible divergence.

    **Critères de qualité:**
    - `signal_confidence_score >= min_confidence` (défaut: 0.7)
    - `signal_divergence_count <= max_divergence` (défaut: 1)
    - Optionnel: filtrer par régime et volatilité

    **Use case:** Trading automatique, alertes, stratégies quantitatives

    **Interprétation:**
    - `signal_confidence_score`: 0.0 (faible) → 1.0 (très fort)
    - `signal_divergence_count`: 0 (cohérent) → 3 (signaux contradictoires)
    - `trend_strength_composite`: -1.0 (forte baisse) → 1.0 (forte hausse)
    - `macro_micro_aligned`: -1 (bearish EUR), 0 (neutre), 1 (bullish EUR)

    **Exemples:**
    - Signaux très forts: `?min_confidence=0.85&max_divergence=0`
    - Risk-off haute confiance: `?min_confidence=0.75&regime=risk_off`
    - Basse volatilité + confiance: `?min_confidence=0.7&volatility_regime=low`
    """
    query = db.query(
        MarketSnapshotM15.time,
        MarketSnapshotM15.signal_confidence_score,
        MarketSnapshotM15.trend_strength_composite,
        MarketSnapshotM15.regime_composite,
        MarketSnapshotM15.volatility_regime,
        MarketSnapshotM15.macro_micro_aligned,
        MarketSnapshotM15.euro_strength_bias,
        MarketSnapshotM15.signal_divergence_count,
        MT5EURUSDM15.close.label('mt5_close'),
        MT5EURUSDM15.open.label('mt5_open')
    ).join(
        MT5EURUSDM15,
        MarketSnapshotM15.mt5_time == MT5EURUSDM15.time
    )

    query = query.filter(
        MarketSnapshotM15.signal_confidence_score >= min_confidence,
        MarketSnapshotM15.signal_divergence_count <= max_divergence
    )

    if regime:
        query = query.filter(MarketSnapshotM15.regime_composite == regime)
    if volatility_regime:
        query = query.filter(MarketSnapshotM15.volatility_regime == volatility_regime)
    if start_date:
        query = query.filter(MarketSnapshotM15.time >= start_date)
    if end_date:
        query = query.filter(MarketSnapshotM15.time <= end_date)

    query = query.order_by(
        desc(MarketSnapshotM15.signal_confidence_score),
        desc(MarketSnapshotM15.time)
    )

    results = query.offset(offset).limit(limit).all()

    if not results:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun signal trouvé avec confiance >= {min_confidence}"
        )

    signals = []
    for row in results:
        signals.append(HighConfidenceSignalResponse(
            time=row.time,
            signal_confidence_score=row.signal_confidence_score,
            trend_strength_composite=row.trend_strength_composite,
            regime_composite=row.regime_composite,
            volatility_regime=row.volatility_regime,
            macro_micro_aligned=row.macro_micro_aligned,
            euro_strength_bias=row.euro_strength_bias,
            signal_divergence_count=row.signal_divergence_count,
            mt5_close=row.mt5_close,
            mt5_open=row.mt5_open
        ))

    return signals



@router.get("/best", response_model=List[HighConfidenceSignalResponse])
def get_best_signals(
    top_n: int = Query(10, ge=1, le=100, description="Nombre de meilleurs signaux à retourner"),
    start_date: Optional[datetime] = Query(None, description="Date de début"),
    end_date: Optional[datetime] = Query(None, description="Date de fin"),
    db: Session = Depends(get_db),
    token: APIToken = Depends(verify_api_token)
):
    """
    Meilleurs signaux (Top N)

    Récupère les N meilleurs signaux basés sur le score de confiance,
    avec divergence = 0 (cohérence maximale).

    **Use case:** Alertes prioritaires, top opportunities

    Retourne les signaux les plus prometteurs uniquement.
    """
    query = db.query(
        MarketSnapshotM15.time,
        MarketSnapshotM15.signal_confidence_score,
        MarketSnapshotM15.trend_strength_composite,
        MarketSnapshotM15.regime_composite,
        MarketSnapshotM15.volatility_regime,
        MarketSnapshotM15.macro_micro_aligned,
        MarketSnapshotM15.euro_strength_bias,
        MarketSnapshotM15.signal_divergence_count,
        MT5EURUSDM15.close.label('mt5_close'),
        MT5EURUSDM15.open.label('mt5_open')
    ).join(
        MT5EURUSDM15,
        MarketSnapshotM15.mt5_time == MT5EURUSDM15.time
    )

    query = query.filter(MarketSnapshotM15.signal_divergence_count == 0)

    if start_date:
        query = query.filter(MarketSnapshotM15.time >= start_date)
    if end_date:
        query = query.filter(MarketSnapshotM15.time <= end_date)

    query = query.order_by(desc(MarketSnapshotM15.signal_confidence_score))

    results = query.limit(top_n).all()

    if not results:
        raise HTTPException(status_code=404, detail="Aucun signal trouvé")

    signals = []
    for row in results:
        signals.append(HighConfidenceSignalResponse(
            time=row.time,
            signal_confidence_score=row.signal_confidence_score,
            trend_strength_composite=row.trend_strength_composite,
            regime_composite=row.regime_composite,
            volatility_regime=row.volatility_regime,
            macro_micro_aligned=row.macro_micro_aligned,
            euro_strength_bias=row.euro_strength_bias,
            signal_divergence_count=row.signal_divergence_count,
            mt5_close=row.mt5_close,
            mt5_open=row.mt5_open
        ))

    return signals



@router.get("/strong-trend", response_model=List[HighConfidenceSignalResponse])
def get_strong_trend_signals(
    min_trend_strength: float = Query(0.5, ge=0.0, le=1.0, description="Force de tendance minimum (valeur absolue)"),
    min_confidence: float = Query(0.6, ge=0.0, le=1.0, description="Score de confiance minimum"),
    direction: Optional[str] = Query(None, description="Direction: 'bullish' ou 'bearish'"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre max de résultats"),
    offset: int = Query(0, ge=0, description="Offset pour pagination"),
    db: Session = Depends(get_db),
    token: APIToken = Depends(verify_api_token)
):
    """
    Signaux avec forte tendance

    Récupère les signaux avec tendance forte et confiance élevée.

    **Paramètres:**
    - `min_trend_strength`: Force minimum (en valeur absolue)
    - `direction`: 'bullish' (hausse) ou 'bearish' (baisse)
    - `min_confidence`: Score de confiance minimum

    **Use case:** Stratégies trend-following, breakouts

    **Interprétation trend_strength_composite:**
    - < -0.5: Forte baisse (bearish)
    - -0.5 à -0.2: Baisse modérée
    - -0.2 à 0.2: Range/Neutre
    - 0.2 à 0.5: Hausse modérée
    - > 0.5: Forte hausse (bullish)
    """
    query = db.query(
        MarketSnapshotM15.time,
        MarketSnapshotM15.signal_confidence_score,
        MarketSnapshotM15.trend_strength_composite,
        MarketSnapshotM15.regime_composite,
        MarketSnapshotM15.volatility_regime,
        MarketSnapshotM15.macro_micro_aligned,
        MarketSnapshotM15.euro_strength_bias,
        MarketSnapshotM15.signal_divergence_count,
        MT5EURUSDM15.close.label('mt5_close'),
        MT5EURUSDM15.open.label('mt5_open')
    ).join(
        MT5EURUSDM15,
        MarketSnapshotM15.mt5_time == MT5EURUSDM15.time
    )

    query = query.filter(MarketSnapshotM15.signal_confidence_score >= min_confidence)

    if direction == "bullish":
        query = query.filter(MarketSnapshotM15.trend_strength_composite >= min_trend_strength)
    elif direction == "bearish":
        query = query.filter(MarketSnapshotM15.trend_strength_composite <= -min_trend_strength)
    else:
        from sqlalchemy import func
        query = query.filter(func.abs(MarketSnapshotM15.trend_strength_composite) >= min_trend_strength)

    from sqlalchemy import func
    query = query.order_by(
        desc(func.abs(MarketSnapshotM15.trend_strength_composite)),
        desc(MarketSnapshotM15.signal_confidence_score)
    )

    results = query.offset(offset).limit(limit).all()

    if not results:
        raise HTTPException(status_code=404, detail="Aucun signal avec forte tendance trouvé")

    signals = []
    for row in results:
        signals.append(HighConfidenceSignalResponse(
            time=row.time,
            signal_confidence_score=row.signal_confidence_score,
            trend_strength_composite=row.trend_strength_composite,
            regime_composite=row.regime_composite,
            volatility_regime=row.volatility_regime,
            macro_micro_aligned=row.macro_micro_aligned,
            euro_strength_bias=row.euro_strength_bias,
            signal_divergence_count=row.signal_divergence_count,
            mt5_close=row.mt5_close,
            mt5_open=row.mt5_open
        ))

    return signals



@router.get("/event-window", response_model=List[HighConfidenceSignalResponse])
def get_event_window_signals(
    active_only: bool = Query(True, description="Seulement les fenêtres d'events actives"),
    min_confidence: float = Query(0.6, ge=0.0, le=1.0, description="Score de confiance minimum"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre max de résultats"),
    offset: int = Query(0, ge=0, description="Offset pour pagination"),
    db: Session = Depends(get_db),
    token: APIToken = Depends(verify_api_token)
):
    """
    Signaux pendant fenêtres d'événements importants

    Récupère les signaux qui se produisent pendant ou proche d'événements
    macro importants (annonces BCE/FED, NFP, etc.).

    **Use case:** Stratégies event-driven, éviter ou exploiter la volatilité

    `event_window_active = True` indique une fenêtre temporelle proche
    d'un événement à fort impact sur EUR/USD.
    """
    query = db.query(
        MarketSnapshotM15.time,
        MarketSnapshotM15.signal_confidence_score,
        MarketSnapshotM15.trend_strength_composite,
        MarketSnapshotM15.regime_composite,
        MarketSnapshotM15.volatility_regime,
        MarketSnapshotM15.macro_micro_aligned,
        MarketSnapshotM15.euro_strength_bias,
        MarketSnapshotM15.signal_divergence_count,
        MT5EURUSDM15.close.label('mt5_close'),
        MT5EURUSDM15.open.label('mt5_open')
    ).join(
        MT5EURUSDM15,
        MarketSnapshotM15.mt5_time == MT5EURUSDM15.time
    )

    if active_only:
        query = query.filter(MarketSnapshotM15.event_window_active == True)

    query = query.filter(MarketSnapshotM15.signal_confidence_score >= min_confidence)

    query = query.order_by(desc(MarketSnapshotM15.time))

    results = query.offset(offset).limit(limit).all()

    if not results:
        raise HTTPException(status_code=404, detail="Aucun signal event-window trouvé")

    signals = []
    for row in results:
        signals.append(HighConfidenceSignalResponse(
            time=row.time,
            signal_confidence_score=row.signal_confidence_score,
            trend_strength_composite=row.trend_strength_composite,
            regime_composite=row.regime_composite,
            volatility_regime=row.volatility_regime,
            macro_micro_aligned=row.macro_micro_aligned,
            euro_strength_bias=row.euro_strength_bias,
            signal_divergence_count=row.signal_divergence_count,
            mt5_close=row.mt5_close,
            mt5_open=row.mt5_open
        ))

    return signals



@router.get("/stats")
def get_signal_stats(
    start_date: Optional[datetime] = Query(None, description="Date de début"),
    end_date: Optional[datetime] = Query(None, description="Date de fin"),
    db: Session = Depends(get_db),
    token: APIToken = Depends(verify_api_token)
):
    """
    Statistiques des signaux

    Analyse agrégée des signaux:
    - Distribution par score de confiance
    - Distribution par divergence
    - Distribution par force de tendance
    - Compteurs par régime

    **Use case:** Quality check, performance analysis
    """
    query = db.query(MarketSnapshotM15)

    if start_date:
        query = query.filter(MarketSnapshotM15.time >= start_date)
    if end_date:
        query = query.filter(MarketSnapshotM15.time <= end_date)

    snapshots = query.all()

    if not snapshots:
        raise HTTPException(status_code=404, detail="Aucune donnée trouvée")

    total = len(snapshots)

    high_confidence = len([s for s in snapshots if s.signal_confidence_score and s.signal_confidence_score >= 0.7])
    medium_confidence = len([s for s in snapshots if s.signal_confidence_score and 0.4 <= s.signal_confidence_score < 0.7])
    low_confidence = len([s for s in snapshots if s.signal_confidence_score and s.signal_confidence_score < 0.4])

    divergence_counts = {}
    for s in snapshots:
        div = s.signal_divergence_count if s.signal_divergence_count is not None else -1
        divergence_counts[div] = divergence_counts.get(div, 0) + 1

    strong_bullish = len([s for s in snapshots if s.trend_strength_composite and s.trend_strength_composite >= 0.5])
    moderate_bullish = len([s for s in snapshots if s.trend_strength_composite and 0.2 <= s.trend_strength_composite < 0.5])
    neutral = len([s for s in snapshots if s.trend_strength_composite and -0.2 <= s.trend_strength_composite < 0.2])
    moderate_bearish = len([s for s in snapshots if s.trend_strength_composite and -0.5 <= s.trend_strength_composite < -0.2])
    strong_bearish = len([s for s in snapshots if s.trend_strength_composite and s.trend_strength_composite < -0.5])

    event_windows = len([s for s in snapshots if s.event_window_active])

    return {
        "total_snapshots": total,
        "period": {
            "start": min(s.time for s in snapshots),
            "end": max(s.time for s in snapshots)
        },
        "confidence_distribution": {
            "high (>=0.7)": high_confidence,
            "medium (0.4-0.7)": medium_confidence,
            "low (<0.4)": low_confidence
        },
        "divergence_distribution": divergence_counts,
        "trend_distribution": {
            "strong_bullish (>=0.5)": strong_bullish,
            "moderate_bullish (0.2-0.5)": moderate_bullish,
            "neutral (-0.2 to 0.2)": neutral,
            "moderate_bearish (-0.5 to -0.2)": moderate_bearish,
            "strong_bearish (<-0.5)": strong_bearish
        },
        "event_windows_active": event_windows
    }
