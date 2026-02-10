"""
Pydantic Schemas pour les données et features
"""

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional



class YahooFinanceResponse(BaseModel):
    """Response pour données Yahoo Finance (Daily)"""
    time: datetime

    eurusd_close: Optional[float] = None
    eurusd_return: Optional[float] = None

    dxy_close: Optional[float] = None
    dxy_return: Optional[float] = None

    eur_yield: Optional[float] = None
    eur_yield_change: Optional[float] = None

    us_yield: Optional[float] = None
    us_yield_change: Optional[float] = None

    yield_spread_eur_us: Optional[float] = None

    vix_close: Optional[float] = None
    vix_change: Optional[float] = None

    risk_sentiment: Optional[str] = None

    created_at: Optional[datetime] = None
    pipeline_run_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)



class DocumentsMacroResponse(BaseModel):
    """Response pour documents macro"""
    time: datetime

    eur_gdp_growth: Optional[float] = None
    us_gdp_growth: Optional[float] = None
    gdp_growth_diff: Optional[float] = None

    eur_inflation_rate: Optional[float] = None
    us_inflation_rate: Optional[float] = None
    inflation_diff: Optional[float] = None

    ecb_rate: Optional[float] = None
    fed_rate: Optional[float] = None
    rate_diff: Optional[float] = None

    eur_trade_balance: Optional[float] = None
    us_trade_balance: Optional[float] = None

    eur_unemployment: Optional[float] = None
    us_unemployment: Optional[float] = None

    created_at: Optional[datetime] = None
    pipeline_run_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)



class TrainingDataResponse(BaseModel):
    """Response pour données d'entraînement complètes (avec JOINs)"""
    time: datetime

    mt5_open: float
    mt5_high: float
    mt5_low: float
    mt5_close: float
    mt5_tick_volume: Optional[float] = None

    close_return: Optional[float] = None
    volatility_1h: Optional[float] = None
    volatility_4h: Optional[float] = None
    momentum_15m: Optional[float] = None
    momentum_1h: Optional[float] = None
    momentum_4h: Optional[float] = None

    eurusd_close: Optional[float] = None
    dxy_close: Optional[float] = None
    vix_close: Optional[float] = None
    yield_spread_eur_us: Optional[float] = None
    risk_sentiment: Optional[str] = None

    eur_gdp_growth: Optional[float] = None
    us_gdp_growth: Optional[float] = None
    eur_inflation_rate: Optional[float] = None
    us_inflation_rate: Optional[float] = None
    ecb_rate: Optional[float] = None
    fed_rate: Optional[float] = None

    macro_micro_aligned: Optional[int] = None
    euro_strength_bias: Optional[int] = None
    regime_composite: Optional[str] = None
    volatility_regime: Optional[str] = None
    signal_confidence_score: Optional[float] = None
    trend_strength_composite: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)
