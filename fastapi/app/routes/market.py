"""
Router Market - Endpoints pour données de marché et snapshots
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List, Optional
from datetime import datetime, timedelta

# Imports depuis airflow (PYTHONPATH configuré par config.py)
from models import MT5EURUSDM15, MarketSnapshotM15

# Imports depuis la nouvelle structure modulaire
from app.core.dependencies import get_db
from app.core.auth import verify_api_token
from app.models.api_token import APIToken
from app.schemas.market import (
    MT5Response,
    MarketSnapshotResponse,
    RegimeDistributionResponse
)

router = APIRouter()


# ============================================================================
# ENDPOINT: Latest Market Data
# ============================================================================

@router.get("/latest", response_model=MarketSnapshotResponse)
def get_latest_market_snapshot(
    db: Session = Depends(get_db),
    token: APIToken = Depends(verify_api_token)
):
    """
    📊 Récupère le dernier snapshot de marché disponible

    Retourne les données les plus récentes incluant:
    - Prix MT5 (M15)
    - Features composites
    - Régimes de marché
    - Scores de confiance

    **Use case:** Dashboard temps réel, monitoring
    """
    snapshot = db.query(MarketSnapshotM15).order_by(desc(MarketSnapshotM15.time)).first()

    if not snapshot:
        raise HTTPException(status_code=404, detail="Aucun snapshot trouvé")

    return snapshot


# ============================================================================
# ENDPOINT: OHLCV M15 Data
# ============================================================================

@router.get("/ohlcv/m15", response_model=List[MT5Response])
def get_mt5_ohlcv(
    start_date: Optional[datetime] = Query(None, description="Date de début (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Date de fin (ISO format)"),
    limit: int = Query(100, ge=1, le=10000, description="Nombre max de résultats"),
    offset: int = Query(0, ge=0, description="Offset pour pagination"),
    db: Session = Depends(get_db),
    token: APIToken = Depends(verify_api_token)
):
    """
    📈 Récupère les données OHLCV MT5 (M15)

    Données haute fréquence (15 minutes) incluant:
    - Prix OHLCV
    - Volume
    - Features microstructure (volatilité, momentum, chandeliers)

    **Use case:** Charting, backtesting, analyse technique

    **Exemple:**
    - Dernières 100 bougies: `?limit=100`
    - Dernières 24h: `?start_date=2026-01-12T00:00:00&limit=96` (96 x 15min = 24h)
    - Période spécifique: `?start_date=2026-01-10T00:00:00&end_date=2026-01-11T00:00:00`
    """
    query = db.query(MT5EURUSDM15)

    # Filtre par date si fourni
    if start_date:
        query = query.filter(MT5EURUSDM15.time >= start_date)
    if end_date:
        query = query.filter(MT5EURUSDM15.time <= end_date)

    # Si aucune date fournie, prendre les dernières données
    query = query.order_by(desc(MT5EURUSDM15.time))

    # Pagination
    results = query.offset(offset).limit(limit).all()

    if not results:
        raise HTTPException(status_code=404, detail="Aucune donnée trouvée pour cette période")

    return results


# ============================================================================
# ENDPOINT: Market Snapshot History
# ============================================================================

@router.get("/snapshot", response_model=List[MarketSnapshotResponse])
def get_market_snapshots(
    start_date: Optional[datetime] = Query(None, description="Date de début (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Date de fin (ISO format)"),
    regime: Optional[str] = Query(None, description="Filtrer par régime: risk_on, risk_off, neutral, volatile"),
    volatility_regime: Optional[str] = Query(None, description="Filtrer par volatilité: low, normal, high"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Score de confiance minimum"),
    limit: int = Query(100, ge=1, le=10000, description="Nombre max de résultats"),
    offset: int = Query(0, ge=0, description="Offset pour pagination"),
    db: Session = Depends(get_db),
    token: APIToken = Depends(verify_api_token)
):
    """
    📊 Récupère l'historique des snapshots de marché avec filtres

    Permet de filtrer par:
    - Plage de dates
    - Régime de marché (risk_on, risk_off, neutral, volatile)
    - Régime de volatilité (low, normal, high)
    - Score de confiance minimum

    **Use case:** Analyse de marché, stratégies basées sur régimes

    **Exemples:**
    - Périodes risk-off: `?regime=risk_off&limit=1000`
    - Haute volatilité + haute confiance: `?volatility_regime=high&min_confidence=0.8`
    - Dernière semaine: `?start_date=2026-01-06T00:00:00&limit=672` (7 jours x 96 bars)
    """
    query = db.query(MarketSnapshotM15)

    # Filtres
    if start_date:
        query = query.filter(MarketSnapshotM15.time >= start_date)
    if end_date:
        query = query.filter(MarketSnapshotM15.time <= end_date)
    if regime:
        query = query.filter(MarketSnapshotM15.regime_composite == regime)
    if volatility_regime:
        query = query.filter(MarketSnapshotM15.volatility_regime == volatility_regime)
    if min_confidence:
        query = query.filter(MarketSnapshotM15.signal_confidence_score >= min_confidence)

    # Tri et pagination
    query = query.order_by(desc(MarketSnapshotM15.time))
    results = query.offset(offset).limit(limit).all()

    if not results:
        raise HTTPException(status_code=404, detail="Aucun snapshot trouvé avec ces critères")

    return results


# ============================================================================
# ENDPOINT: Market Regimes Distribution
# ============================================================================

@router.get("/regimes", response_model=List[RegimeDistributionResponse])
def get_regime_distribution(
    start_date: Optional[datetime] = Query(None, description="Date de début"),
    end_date: Optional[datetime] = Query(None, description="Date de fin"),
    db: Session = Depends(get_db),
    token: APIToken = Depends(verify_api_token)
):
    """
    📊 Distribution des régimes de marché

    Analyse la répartition des différents régimes sur une période donnée:
    - risk_on: Sentiment haussier, appétit pour le risque
    - risk_off: Sentiment baissier, aversion au risque
    - neutral: Marché sans direction claire
    - volatile: Forte volatilité, incertitude

    **Use case:** Analyse macroéconomique, stratégies adaptatives

    Retourne le nombre et pourcentage de chaque régime.
    """
    query = db.query(MarketSnapshotM15)

    # Filtres dates
    if start_date:
        query = query.filter(MarketSnapshotM15.time >= start_date)
    if end_date:
        query = query.filter(MarketSnapshotM15.time <= end_date)

    # Compter tous les enregistrements
    total = query.count()

    if total == 0:
        raise HTTPException(status_code=404, detail="Aucune donnée trouvée pour cette période")

    # Compter par régime
    regimes = ["risk_on", "risk_off", "neutral", "volatile"]
    distribution = []

    for regime in regimes:
        count = query.filter(MarketSnapshotM15.regime_composite == regime).count()
        percentage = (count / total) * 100 if total > 0 else 0

        distribution.append(
            RegimeDistributionResponse(
                regime=regime,
                count=count,
                percentage=round(percentage, 2)
            )
        )

    return distribution


# ============================================================================
# ENDPOINT: Latest OHLCV (Quick Access)
# ============================================================================

@router.get("/ohlcv/latest", response_model=MT5Response)
def get_latest_ohlcv(
    db: Session = Depends(get_db),
    token: APIToken = Depends(verify_api_token)
):
    """
    📈 Dernier prix OHLCV disponible

    **Use case:** Monitoring temps réel, widgets de prix

    Retourne uniquement la dernière bougie M15.
    """
    ohlcv = db.query(MT5EURUSDM15).order_by(desc(MT5EURUSDM15.time)).first()

    if not ohlcv:
        raise HTTPException(status_code=404, detail="Aucune donnée OHLCV trouvée")

    return ohlcv


# ============================================================================
# ENDPOINT: Market Statistics
# ============================================================================

@router.get("/stats")
def get_market_stats(
    start_date: Optional[datetime] = Query(None, description="Date de début"),
    end_date: Optional[datetime] = Query(None, description="Date de fin"),
    db: Session = Depends(get_db),
    token: APIToken = Depends(verify_api_token)
):
    """
    📊 Statistiques de marché agrégées

    Calcule des statistiques sur une période:
    - Nombre total de snapshots
    - Période couverte (première et dernière date)
    - Distribution des régimes
    - Score de confiance moyen
    - Régime de volatilité dominant

    **Use case:** Analyse de période, reporting
    """
    query = db.query(MarketSnapshotM15)

    # Filtres dates
    if start_date:
        query = query.filter(MarketSnapshotM15.time >= start_date)
    if end_date:
        query = query.filter(MarketSnapshotM15.time <= end_date)

    # Récupérer toutes les données
    snapshots = query.all()

    if not snapshots:
        raise HTTPException(status_code=404, detail="Aucune donnée trouvée")

    # Calculer les stats
    total_count = len(snapshots)
    first_date = min(s.time for s in snapshots)
    last_date = max(s.time for s in snapshots)

    # Scores de confiance moyens
    confidence_scores = [s.signal_confidence_score for s in snapshots if s.signal_confidence_score is not None]
    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

    # Distribution régimes
    regimes = {}
    for s in snapshots:
        regime = s.regime_composite or "unknown"
        regimes[regime] = regimes.get(regime, 0) + 1

    # Distribution volatilité
    volatility_regimes = {}
    for s in snapshots:
        vol_regime = s.volatility_regime or "unknown"
        volatility_regimes[vol_regime] = volatility_regimes.get(vol_regime, 0) + 1

    return {
        "total_snapshots": total_count,
        "period": {
            "start": first_date,
            "end": last_date,
            "days": (last_date - first_date).days
        },
        "average_confidence_score": round(avg_confidence, 3),
        "regime_distribution": regimes,
        "volatility_distribution": volatility_regimes
    }
