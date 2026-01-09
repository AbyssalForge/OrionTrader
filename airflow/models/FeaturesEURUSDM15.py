"""
SILVER LAYER - Features Engineering
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Index
from datetime import datetime
from .base import Base


class FeaturesEURUSDM15(Base):
    """
    Features unifiées - EURUSD M15
    Combine MT5 + Stooq + Eurostat avec feature engineering
    Prêt pour le ML (mais sans labels)
    """
    __tablename__ = 'features_eurusd_m15'

    time = Column(DateTime(timezone=True), primary_key=True)

    # ===== MT5 Raw Data =====
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    tick_volume = Column(Float)

    # ===== MT5 Features (Microstructure) =====
    close_diff = Column(Float)
    close_return = Column(Float)
    high_low_range = Column(Float)
    volatility_1h = Column(Float)
    volatility_4h = Column(Float)
    momentum_15m = Column(Float)
    momentum_1h = Column(Float)
    momentum_4h = Column(Float)
    body = Column(Float)
    upper_shadow = Column(Float)
    lower_shadow = Column(Float)

    # ===== Stooq Features (Régime de Marché) =====
    # DXY (Dollar Index)
    dxy_close = Column(Float)
    dxy_trend_1h = Column(Float)
    dxy_trend_4h = Column(Float)
    dxy_strength = Column(Float)

    # VIX (Volatilité / Stress)
    vix_close = Column(Float)
    vix_level = Column(Float)
    vix_change = Column(Float)
    market_stress = Column(Integer)  # 0 ou 1

    # S&P 500 (Risk-on/off)
    spx_close = Column(Float)
    spx_trend = Column(Float)
    risk_on = Column(Integer)  # 0 ou 1

    # Gold (Safe Haven)
    gold_close = Column(Float)
    gold_trend = Column(Float)
    safe_haven = Column(Integer)  # 0 ou 1

    # ===== Eurostat Features (Fondamentaux) =====
    eurozone_pib = Column(Float)
    pib_change = Column(Float)
    pib_growth = Column(Integer)  # 0 ou 1

    eurozone_cpi = Column(Float)
    cpi_change = Column(Float)
    inflation_pressure = Column(Integer)  # 0 ou 1

    # ===== Economic Events =====
    event_title = Column(String(200))
    event_impact = Column(String(10))
    event_impact_score = Column(Integer)  # 1, 2, 3

    # ===== Features Composites =====
    macro_micro_aligned = Column(Integer)  # 0 ou 1
    euro_strength_bias = Column(Integer)  # 0, 1, 2

    # ===== Metadata =====
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    pipeline_run_id = Column(String(100))

    __table_args__ = (
        Index('idx_features_time', 'time'),
        Index('idx_features_pipeline', 'pipeline_run_id'),
    )
