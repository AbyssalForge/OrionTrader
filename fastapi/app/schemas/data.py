"""
Pydantic Schemas pour les données et features
"""

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


# ============================================================================
# YAHOO FINANCE SCHEMAS
# ============================================================================

class YahooFinanceResponse(BaseModel):
    """Response pour données Yahoo Finance (Daily)"""
    time: datetime

    # EUR/USD spot
    eurusd_close: Optional[float] = None
    eurusd_return: Optional[float] = None

    # DXY (US Dollar Index)
    dxy_close: Optional[float] = None
    dxy_return: Optional[float] = None

    # EUR Yield
    eur_yield: Optional[float] = None
    eur_yield_change: Optional[float] = None

    # US Yield
    us_yield: Optional[float] = None
    us_yield_change: Optional[float] = None

    # Spread
    yield_spread_eur_us: Optional[float] = None

    # VIX
    vix_close: Optional[float] = None
    vix_change: Optional[float] = None

    # Risk metrics
    risk_sentiment: Optional[str] = None

    # Metadata
    created_at: Optional[datetime] = None
    pipeline_run_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# DOCUMENTS MACRO SCHEMAS
# ============================================================================

class DocumentsMacroResponse(BaseModel):
    """Response pour documents macro"""
    time: datetime

    # PIB
    eur_gdp_growth: Optional[float] = None
    us_gdp_growth: Optional[float] = None
    gdp_growth_diff: Optional[float] = None

    # Inflation
    eur_inflation_rate: Optional[float] = None
    us_inflation_rate: Optional[float] = None
    inflation_diff: Optional[float] = None

    # Taux directeurs
    ecb_rate: Optional[float] = None
    fed_rate: Optional[float] = None
    rate_diff: Optional[float] = None

    # Balances commerciales
    eur_trade_balance: Optional[float] = None
    us_trade_balance: Optional[float] = None

    # Chômage
    eur_unemployment: Optional[float] = None
    us_unemployment: Optional[float] = None

    # Metadata
    created_at: Optional[datetime] = None
    pipeline_run_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# SCHEMAS POUR TRAINING DATA (FULL JOIN)
# ============================================================================

class TrainingDataResponse(BaseModel):
    """Response pour données d'entraînement complètes (avec JOINs)"""
    # Time
    time: datetime

    # MT5 OHLCV
    mt5_open: float
    mt5_high: float
    mt5_low: float
    mt5_close: float
    mt5_tick_volume: Optional[float] = None

    # MT5 Features
    close_return: Optional[float] = None
    volatility_1h: Optional[float] = None
    volatility_4h: Optional[float] = None
    momentum_15m: Optional[float] = None
    momentum_1h: Optional[float] = None
    momentum_4h: Optional[float] = None

    # Yahoo Finance
    eurusd_close: Optional[float] = None
    dxy_close: Optional[float] = None
    vix_close: Optional[float] = None
    yield_spread_eur_us: Optional[float] = None
    risk_sentiment: Optional[str] = None

    # Macro
    eur_gdp_growth: Optional[float] = None
    us_gdp_growth: Optional[float] = None
    eur_inflation_rate: Optional[float] = None
    us_inflation_rate: Optional[float] = None
    ecb_rate: Optional[float] = None
    fed_rate: Optional[float] = None

    # Snapshot Features
    macro_micro_aligned: Optional[int] = None
    euro_strength_bias: Optional[int] = None
    regime_composite: Optional[str] = None
    volatility_regime: Optional[str] = None
    signal_confidence_score: Optional[float] = None
    trend_strength_composite: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)
