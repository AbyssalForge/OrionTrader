"""
Modèles SQLAlchemy pour l'architecture Data Lake (Bronze/Silver/Gold)
Architecture:
- Bronze (Raw): Données brutes de chaque source
- Silver (Features): Données transformées et enrichies
- Gold (ML): Datasets préparés pour les modèles
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Index, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

# =============================================================================
# BRONZE LAYER - Données brutes
# =============================================================================

class RawMT5EURUSDM15(Base):
    """
    Données brutes MT5 - EURUSD M15
    Source: MetaTrader 5
    Fréquence: 15 minutes
    """
    __tablename__ = 'raw_mt5_eurusd_m15'

    time = Column(DateTime(timezone=True), primary_key=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    tick_volume = Column(Float)
    spread = Column(Integer)
    real_volume = Column(Float)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    pipeline_run_id = Column(String(100))

    __table_args__ = (
        Index('idx_raw_mt5_time', 'time'),
        Index('idx_raw_mt5_pipeline', 'pipeline_run_id'),
    )


class RawStooqDaily(Base):
    """
    Données brutes Stooq - Actifs macro (daily)
    Source: Stooq API
    Fréquence: Daily
    """
    __tablename__ = 'raw_stooq_daily'

    time = Column(DateTime(timezone=True), primary_key=True)
    symbol = Column(String(20), primary_key=True)  # 'DXY', 'EURUSD', 'GOLD', etc.

    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float)

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    pipeline_run_id = Column(String(100))

    __table_args__ = (
        Index('idx_raw_stooq_time', 'time'),
        Index('idx_raw_stooq_symbol', 'symbol'),
        Index('idx_raw_stooq_pipeline', 'pipeline_run_id'),
    )


class RawEurostatMacro(Base):
    """
    Données brutes Eurostat - Indicateurs macro
    Source: Eurostat API
    Fréquence: Monthly/Quarterly
    """
    __tablename__ = 'raw_eurostat_macro'

    time = Column(DateTime(timezone=True), primary_key=True)
    indicator = Column(String(50), primary_key=True)  # 'PIB', 'CPI', etc.

    value = Column(Float, nullable=False)
    unit = Column(String(20))  # 'INDEX', 'PERCENT', etc.

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    pipeline_run_id = Column(String(100))

    __table_args__ = (
        Index('idx_raw_eurostat_time', 'time'),
        Index('idx_raw_eurostat_indicator', 'indicator'),
        Index('idx_raw_eurostat_pipeline', 'pipeline_run_id'),
    )


class RawEconomicEvents(Base):
    """
    Événements économiques
    Source: ForexFactory / Custom
    """
    __tablename__ = 'raw_economic_events'

    time = Column(DateTime(timezone=True), primary_key=True)
    title = Column(String(200), primary_key=True)

    impact = Column(String(10))  # 'High', 'Medium', 'Low'
    country = Column(String(10))
    currency = Column(String(10))

    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    pipeline_run_id = Column(String(100))

    __table_args__ = (
        Index('idx_raw_events_time', 'time'),
        Index('idx_raw_events_impact', 'impact'),
    )


# =============================================================================
# SILVER LAYER - Features Engineering
# =============================================================================

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


# =============================================================================
# GOLD LAYER - ML Datasets
# =============================================================================

class MLClassificationDataset(Base):
    """
    Dataset pour modèle de classification (Buy / Sell / Hold)
    Features + Label
    """
    __tablename__ = 'ml_classification_dataset'

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime(timezone=True), nullable=False, index=True)

    # ===== Label (Cible) =====
    signal = Column(String(10), nullable=False)  # 'BUY', 'SELL', 'HOLD'
    signal_encoded = Column(Integer, nullable=False)  # 0, 1, 2

    # Forward return (pour calculer le label)
    forward_return_1h = Column(Float)
    forward_return_4h = Column(Float)

    # ===== Features (référence à features_eurusd_m15) =====
    # On stocke juste time + signal
    # Les features sont joinées depuis features_eurusd_m15

    # ===== Split info =====
    split = Column(String(10))  # 'train', 'val', 'test'

    # ===== Metadata =====
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    pipeline_run_id = Column(String(100))

    __table_args__ = (
        Index('idx_ml_class_time', 'time'),
        Index('idx_ml_class_split', 'split'),
        Index('idx_ml_class_signal', 'signal_encoded'),
    )


class MLRegressionDataset(Base):
    """
    Dataset pour modèle de régression (prédiction du return futur)
    """
    __tablename__ = 'ml_regression_dataset'

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime(timezone=True), nullable=False, index=True)

    # ===== Label (Cible) =====
    target_return_15m = Column(Float, nullable=False)
    target_return_1h = Column(Float, nullable=False)
    target_return_4h = Column(Float, nullable=False)

    # ===== Split info =====
    split = Column(String(10))  # 'train', 'val', 'test'

    # ===== Metadata =====
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    pipeline_run_id = Column(String(100))

    __table_args__ = (
        Index('idx_ml_reg_time', 'time'),
        Index('idx_ml_reg_split', 'split'),
    )


class RLEnvironmentState(Base):
    """
    Dataset pour Reinforcement Learning
    State, Action, Reward pour entraînement RL
    """
    __tablename__ = 'rl_environment_state'

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime(timezone=True), nullable=False, index=True)

    # ===== State (référence à features_eurusd_m15) =====
    # Les features sont dans features_eurusd_m15

    # ===== Action prise =====
    action = Column(Integer)  # 0: Hold, 1: Buy, 2: Sell, 3: Close
    position_size = Column(Float)  # Taille de la position (0-1)

    # ===== Reward =====
    reward = Column(Float)
    pnl = Column(Float)  # Profit/Loss
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)

    # ===== Next state =====
    next_time = Column(DateTime(timezone=True))

    # ===== Episode info =====
    episode_id = Column(Integer)
    step = Column(Integer)
    done = Column(Boolean)  # Episode terminé ?

    # ===== Split info =====
    split = Column(String(10))  # 'train', 'val', 'test'

    # ===== Metadata =====
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    pipeline_run_id = Column(String(100))

    __table_args__ = (
        Index('idx_rl_time', 'time'),
        Index('idx_rl_episode', 'episode_id'),
        Index('idx_rl_split', 'split'),
    )


# =============================================================================
# Helper Functions
# =============================================================================

def get_engine(connection_string):
    """
    Crée un engine SQLAlchemy
    """
    return create_engine(connection_string, echo=False)


def get_session(engine):
    """
    Crée une session SQLAlchemy
    """
    Session = sessionmaker(bind=engine)
    return Session()


def create_all_tables(engine):
    """
    Crée toutes les tables dans la base de données
    """
    Base.metadata.create_all(engine)
    print("✅ Toutes les tables ont été créées")


def drop_all_tables(engine):
    """
    Supprime toutes les tables (DANGER!)
    """
    Base.metadata.drop_all(engine)
    print("⚠ Toutes les tables ont été supprimées")
