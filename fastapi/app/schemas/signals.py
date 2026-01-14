"""
Pydantic Schemas pour les signaux de trading
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


# ============================================================================
# SCHEMAS POUR SIGNAUX DE TRADING
# ============================================================================

class HighConfidenceSignalResponse(BaseModel):
    """Response pour signaux haute confiance"""
    time: datetime
    signal_confidence_score: float = Field(..., ge=0.7, le=1.0)
    trend_strength_composite: float
    regime_composite: str
    volatility_regime: str
    macro_micro_aligned: Optional[int] = None
    euro_strength_bias: Optional[int] = None
    signal_divergence_count: int

    # Prix MT5 associé
    mt5_close: float
    mt5_open: float

    model_config = ConfigDict(from_attributes=True)
