"""
Pydantic schemas pour validation et sérialisation
"""

from .common import HealthResponse, PipelineStatsResponse, RegimeDistributionResponse
from .market import MT5Response, MarketSnapshotResponse
from .data import YahooFinanceResponse, DocumentsMacroResponse, TrainingDataResponse
from .signals import HighConfidenceSignalResponse
from .model import (
    SimplePredictionRequest,
    PredictionRequest,
    BatchPredictionRequest,
    PredictionResponse,
    BatchPredictionResponse,
    ModelInfo,
    ModelMetrics
)

__all__ = [
    "HealthResponse",
    "PipelineStatsResponse",
    "RegimeDistributionResponse",
    "MT5Response",
    "MarketSnapshotResponse",
    "YahooFinanceResponse",
    "DocumentsMacroResponse",
    "TrainingDataResponse",
    "HighConfidenceSignalResponse",
    "SimplePredictionRequest",
    "PredictionRequest",
    "BatchPredictionRequest",
    "PredictionResponse",
    "BatchPredictionResponse",
    "ModelInfo",
    "ModelMetrics",
]
