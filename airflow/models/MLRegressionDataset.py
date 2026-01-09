"""
GOLD LAYER - Dataset pour régression ML
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Index
from datetime import datetime
from .base import Base


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
