"""
GOLD LAYER - Dataset pour Reinforcement Learning
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Index
from datetime import datetime
from .base import Base


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
