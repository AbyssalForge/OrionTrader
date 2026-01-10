"""
TABLE 2 - Source Yahoo Finance API
Indices financiers quotidiens
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Index
from datetime import datetime
from .base import Base


class YahooFinanceDaily(Base):
    """
    Table 2/3 - Yahoo Finance API

    Source: Yahoo Finance API (yfinance)
    Fréquence: Daily (quotidien)
    Type: Indices financiers + Régime de marché

    Colonnes: 14 (4 indices × 2-4 features chacun)
    Volume: ~500 lignes pour 2 ans
    Taille: ~50 KB

    Indices:
    - DXY (Dollar Index): Force du dollar
    - VIX (Volatilité): Stress de marché
    - SPX (S&P 500): Appétit pour le risque
    - Gold (Or): Safe haven

    Utilisation ML:
    - Capture le régime de marché global
    - Contexte macro quotidien
    - Complémentaire aux prix M15
    """
    __tablename__ = 'yahoo_finance_daily'

    time = Column(DateTime(timezone=True), primary_key=True)

    # ===== S&P 500 - Appétit pour le risque (3 colonnes) =====
    spx_close = Column(Float)           # Niveau S&P 500
    spx_trend = Column(Float)           # Tendance (pct_change 5j)
    risk_on = Column(Integer)           # Binaire: SPX hausse = risk on

    # ===== Gold - Safe Haven (3 colonnes) =====
    gold_close = Column(Float)          # Prix de l'or
    gold_trend = Column(Float)          # Tendance (pct_change 5j)
    safe_haven = Column(Integer)        # Binaire: Gold hausse = safe haven

    # ===== DXY (Dollar Index) - Force du dollar (4 colonnes) =====
    dxy_close = Column(Float)           # Niveau DXY
    dxy_trend_1h = Column(Float)        # Tendance court terme
    dxy_trend_4h = Column(Float)        # Tendance moyen terme
    dxy_strength = Column(Float)        # Force relative vs moyenne mobile

    # ===== VIX (Volatilité) - Stress de marché (4 colonnes) =====
    vix_close = Column(Float)           # Niveau VIX
    vix_level = Column(Float)           # Niveau relatif (vs moyenne)
    vix_change = Column(Float)          # Variation % quotidienne
    market_stress = Column(Integer)     # Binaire: VIX > 20 = stress

    # ===== Metadata (2 colonnes) =====
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    pipeline_run_id = Column(String(100))

    __table_args__ = (
        Index('idx_yahoo_time', 'time'),
        Index('idx_yahoo_pipeline', 'pipeline_run_id'),
    )
