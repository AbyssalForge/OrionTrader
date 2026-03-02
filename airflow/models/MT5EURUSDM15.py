"""
TABLE 1 - Source MT5 Local
Données haute fréquence M15 (15 minutes)
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Index
from datetime import datetime
from .base import Base


class MT5EURUSDM15(Base):
    """
    Table 1/3 - MT5 Local Server

    Source: Serveur MetaTrader 5 local
    Fréquence: M15 (15 minutes)
    Type: Prix + Microstructure

    Colonnes: 17 (6 OHLCV + 11 features microstructure)
    Volume: ~70,000 lignes pour 2 ans
    Taille: ~20 MB

    Utilisation ML:
    - Features de base pour tous les modèles
    - Capture la microstructure de marché
    - Volatilité et momentum haute fréquence
    """
    __tablename__ = 'mt5_eurusd_m15'

    time = Column(DateTime(timezone=True), primary_key=True)

    # ===== OHLCV Raw Data (6 colonnes) =====
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    tick_volume = Column(Float)

    # ===== Features Microstructure (11 colonnes) =====
    # Variations de prix
    close_diff = Column(Float)          # Différence close vs close précédent
    close_return = Column(Float)        # Return % close vs close précédent
    high_low_range = Column(Float)      # Range high-low

    # Volatilité multi-horizon
    volatility_1h = Column(Float)       # Volatilité 1 heure
    volatility_4h = Column(Float)       # Volatilité 4 heures

    # Momentum multi-horizon
    momentum_15m = Column(Float)        # Momentum 15 minutes
    momentum_1h = Column(Float)         # Momentum 1 heure
    momentum_4h = Column(Float)         # Momentum 4 heures

    # Analyse chandelier
    body = Column(Float)                # Taille du corps (|close-open|)
    upper_shadow = Column(Float)        # Mèche haute (high-max(open,close))
    lower_shadow = Column(Float)        # Mèche basse (min(open,close)-low)

    # ===== Metadata (2 colonnes) =====
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    pipeline_run_id = Column(String(100))

    __table_args__ = (
        Index('idx_mt5_time', 'time'),
        Index('idx_mt5_pipeline', 'pipeline_run_id'),
    )
