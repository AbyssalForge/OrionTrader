"""
TABLE 4 - Market Snapshot M15 (Composite)
Table de jointure avec features composites calculées
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, ForeignKey, Index
from datetime import datetime
from .base import Base


class MarketSnapshotM15(Base):
    """
    Table 4/4 - Market Snapshot M15 (Composite)

    Type: Table de jointure avec foreign keys + features calculées
    Fréquence: M15 (15 minutes) - alignée sur MT5

    Architecture:
    - Foreign keys vers les 3 tables sources (MT5, Yahoo, Documents)
    - Features composites multi-sources pré-calculées
    - Pas de duplication des données sources (juste des références)

    Utilisation:
    - Simplifie les requêtes ML (1 seul SELECT avec JOINs)
    - Features de haut niveau pré-calculées
    - Identification rapide des opportunités de trading

    Volume: ~70,000 lignes pour 2 ans (aligné sur MT5)
    Taille: ~5 MB (léger car pas de duplication)
    """
    __tablename__ = 'market_snapshot_m15'

    # ===== Primary Key =====
    time = Column(DateTime(timezone=True), primary_key=True)

    # ===== Foreign Keys (références vers tables sources) =====
    mt5_time = Column(DateTime(timezone=True), ForeignKey('mt5_eurusd_m15.time'), nullable=False)
    yahoo_time = Column(DateTime(timezone=True), ForeignKey('yahoo_finance_daily.time'), nullable=True)
    docs_time = Column(DateTime(timezone=True), ForeignKey('documents_macro.time'), nullable=True)

    # ===== Features composites multi-sources (2 colonnes) =====
    # Alignement macro/micro
    macro_micro_aligned = Column(Integer)           # -1 (bearish EUR), 0 (neutral), 1 (bullish EUR)
    # Biais fondamental EUR
    euro_strength_bias = Column(Integer)            # -1 (faible), 0 (neutre), 1 (fort)

    # ===== Régimes et classifications (2 colonnes) =====
    # Régime de marché global
    regime_composite = Column(String(20))           # 'risk_on', 'risk_off', 'neutral', 'volatile'
    # Régime de volatilité
    volatility_regime = Column(String(20))          # 'low', 'normal', 'high'

    # ===== Scores et métriques (3 colonnes) =====
    # Score de confiance du signal (0.0 = faible, 1.0 = fort)
    signal_confidence_score = Column(Float)         # 0.0 - 1.0
    # Nombre de divergences détectées (0 = cohérent, 3 = confus)
    signal_divergence_count = Column(Integer)       # 0-3
    # Force de la tendance composite
    trend_strength_composite = Column(Float)        # -1.0 (forte baisse) - 1.0 (forte hausse)

    # ===== Event management (1 colonne) =====
    # Indique si on est dans une fenêtre d'event important
    event_window_active = Column(Boolean)           # True si proche d'un event à fort impact

    # ===== Metadata (2 colonnes) =====
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    pipeline_run_id = Column(String(100))

    __table_args__ = (
        # Index sur time pour requêtes temporelles rapides
        Index('idx_snapshot_time', 'time'),
        # Index sur foreign keys pour JOINs rapides
        Index('idx_snapshot_mt5_time', 'mt5_time'),
        Index('idx_snapshot_yahoo_time', 'yahoo_time'),
        Index('idx_snapshot_docs_time', 'docs_time'),
        # Index composites pour filtrage ML
        Index('idx_snapshot_regime', 'regime_composite', 'volatility_regime'),
        Index('idx_snapshot_confidence', 'signal_confidence_score'),
        Index('idx_snapshot_pipeline', 'pipeline_run_id'),
    )
