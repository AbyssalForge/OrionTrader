"""
GOLD LAYER - Dataset pour classification ML
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Index
from datetime import datetime
from .base import Base


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
