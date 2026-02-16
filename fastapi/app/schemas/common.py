"""
Schemas communs utilisés par plusieurs endpoints
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class HealthResponse(BaseModel):
    """Response pour health check"""
    status: str = Field(..., description="ok ou error")
    database: str = Field(..., description="connected ou disconnected")
    timestamp: datetime
    tables: Optional[dict] = Field(None, description="Nombre de lignes par table")


class PipelineStatsResponse(BaseModel):
    """Response pour statistiques pipeline"""
    total_runs: int
    last_run_id: Optional[str] = None
    last_run_time: Optional[datetime] = None
    tables_summary: dict = Field(..., description="Résumé par table")


class RegimeDistributionResponse(BaseModel):
    """Response pour distribution des régimes"""
    regime: str
    count: int
    percentage: float


class DateRangeQuery(BaseModel):
    """Query parameters pour filtrage par date"""
    start_date: Optional[datetime] = Field(None, description="Date de début (ISO format)")
    end_date: Optional[datetime] = Field(None, description="Date de fin (ISO format)")
    limit: int = Field(100, ge=1, le=10000, description="Nombre max de résultats")
    offset: int = Field(0, ge=0, description="Offset pour pagination")
