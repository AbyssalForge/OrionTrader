"""
Pydantic Schemas pour les données de marché
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional



class MT5Response(BaseModel):
    """Response pour données MT5 (M15)"""
    time: datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: Optional[float] = None

    close_diff: Optional[float] = None
    close_return: Optional[float] = None
    high_low_range: Optional[float] = None

    volatility_1h: Optional[float] = None
    volatility_4h: Optional[float] = None

    momentum_15m: Optional[float] = None
    momentum_1h: Optional[float] = None
    momentum_4h: Optional[float] = None

    body: Optional[float] = None
    upper_shadow: Optional[float] = None
    lower_shadow: Optional[float] = None

    created_at: Optional[datetime] = None
    pipeline_run_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)



class MarketSnapshotResponse(BaseModel):
    """Response pour Market Snapshot (M15)"""
    time: datetime

    mt5_time: datetime
    yahoo_time: Optional[datetime] = None
    docs_time: Optional[datetime] = None

    macro_micro_aligned: Optional[int] = Field(None, description="-1 (bearish EUR), 0 (neutral), 1 (bullish EUR)")
    euro_strength_bias: Optional[int] = Field(None, description="-1 (faible), 0 (neutre), 1 (fort)")

    regime_composite: Optional[str] = Field(None, description="risk_on, risk_off, neutral, volatile")
    volatility_regime: Optional[str] = Field(None, description="low, normal, high")

    signal_confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="0.0 (faible) - 1.0 (fort)")
    signal_divergence_count: Optional[int] = Field(None, ge=0, le=3, description="0-3 divergences")
    trend_strength_composite: Optional[float] = Field(None, ge=-1.0, le=1.0, description="-1.0 (forte baisse) - 1.0 (forte hausse)")

    event_window_active: Optional[bool] = None

    created_at: Optional[datetime] = None
    pipeline_run_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)



class RegimeDistributionResponse(BaseModel):
    """Response pour distribution des régimes"""
    regime: str
    count: int
    percentage: float

    model_config = ConfigDict(from_attributes=True)
