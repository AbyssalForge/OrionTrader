"""
Pydantic schemas pour validation et sérialisation
"""

from .common import HealthResponse, PipelineStatsResponse, RegimeDistributionResponse
from .market import MT5Response, MarketSnapshotResponse
from .data import YahooFinanceResponse, DocumentsMacroResponse, TrainingDataResponse
from .signals import HighConfidenceSignalResponse

__all__ = [
    # Common
    "HealthResponse",
    "PipelineStatsResponse",
    "RegimeDistributionResponse",
    # Market
    "MT5Response",
    "MarketSnapshotResponse",
    # Data
    "YahooFinanceResponse",
    "DocumentsMacroResponse",
    "TrainingDataResponse",
    # Signals
    "HighConfidenceSignalResponse",
]
