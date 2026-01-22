"""
Schémas Pydantic pour les endpoints Model/ML
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class SimplePredictionRequest(BaseModel):
    """
    Requête de prédiction avec données brutes (comme dans l'ETL)
    Les features complexes seront calculées automatiquement
    """
    # Prix OHLCV (obligatoire)
    open: float = Field(..., description="Prix d'ouverture")
    high: float = Field(..., description="Prix le plus haut")
    low: float = Field(..., description="Prix le plus bas")
    close: float = Field(..., description="Prix de clôture")
    tick_volume: float = Field(..., description="Volume")

    # Indicateurs externes optionnels (si disponibles)
    spx_close: Optional[float] = Field(None, description="S&P 500 close")
    spx_trend: Optional[float] = Field(None, description="S&P 500 trend")
    risk_on: Optional[float] = Field(None, description="Risk-on score")
    gold_close: Optional[float] = Field(None, description="Gold close")
    gold_trend: Optional[float] = Field(None, description="Gold trend")
    safe_haven: Optional[float] = Field(None, description="Safe haven score")
    dxy_close: Optional[float] = Field(None, description="Dollar Index close")
    dxy_trend_1h: Optional[float] = Field(None, description="DXY trend 1h")
    dxy_trend_4h: Optional[float] = Field(None, description="DXY trend 4h")
    us10y_close: Optional[float] = Field(None, description="US 10Y yield")
    us10y_trend: Optional[float] = Field(None, description="US 10Y trend")
    vix_close: Optional[float] = Field(None, description="VIX close")
    vix_spike: Optional[float] = Field(None, description="VIX spike indicator")

    class Config:
        json_schema_extra = {
            "example": {
                "open": 1.0845,
                "high": 1.0855,
                "low": 1.0840,
                "close": 1.0850,
                "tick_volume": 1000,
                "spx_close": 4500.0,
                "gold_close": 2000.0,
                "dxy_close": 104.5,
                "us10y_close": 4.5,
                "vix_close": 15.0
            }
        }


class PredictionRequest(BaseModel):
    """
    Requête de prédiction avec features complètes (avancé)
    """
    features: Dict[str, float] = Field(
        ...,
        description="Dictionnaire des features pour la prédiction",
        example={
            "close": 1.0850,
            "volatility_1h": 0.0015,
            "momentum_15m": 0.002,
            "rsi_14": 55.5
        }
    )

    class Config:
        json_schema_extra = {
            "example": {
                "features": {
                    "close": 1.0850,
                    "open": 1.0845,
                    "high": 1.0855,
                    "low": 1.0840,
                    "volume": 1000,
                    "volatility_1h": 0.0015,
                    "volatility_4h": 0.0020,
                    "momentum_15m": 0.002,
                    "momentum_1h": 0.003,
                    "momentum_4h": 0.005,
                    "rsi_14": 55.5,
                    "body_ratio": 0.6,
                    "upper_shadow_ratio": 0.2,
                    "lower_shadow_ratio": 0.2
                }
            }
        }


class BatchPredictionRequest(BaseModel):
    """
    Requête de prédiction en batch avec données brutes
    """
    predictions: List[SimplePredictionRequest] = Field(
        ...,
        description="Liste de données OHLCV pour prédictions multiples",
        min_length=1
    )

    class Config:
        json_schema_extra = {
            "example": {
                "predictions": [
                    {
                        "open": 1.0845,
                        "high": 1.0855,
                        "low": 1.0840,
                        "close": 1.0850,
                        "tick_volume": 1000
                    },
                    {
                        "open": 1.0850,
                        "high": 1.0865,
                        "low": 1.0845,
                        "close": 1.0860,
                        "tick_volume": 1200
                    }
                ]
            }
        }


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class PredictionResponse(BaseModel):
    """
    Réponse de prédiction avec probabilités
    """
    prediction: int = Field(..., description="Classe prédite: 0=SHORT, 1=NEUTRAL, 2=LONG")
    prediction_label: str = Field(..., description="Label de la prédiction")
    probabilities: Dict[str, float] = Field(..., description="Probabilités par classe")
    confidence: float = Field(..., ge=0, le=1, description="Confiance de la prédiction (max proba)")
    model_version: Optional[str] = Field(None, description="Version du modèle utilisé")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp de la prédiction")

    class Config:
        json_schema_extra = {
            "example": {
                "prediction": 2,
                "prediction_label": "LONG",
                "probabilities": {
                    "SHORT": 0.15,
                    "NEUTRAL": 0.25,
                    "LONG": 0.60
                },
                "confidence": 0.60,
                "model_version": "1",
                "timestamp": "2024-01-21T16:00:00"
            }
        }


class BatchPredictionResponse(BaseModel):
    """
    Réponse de prédiction en batch
    """
    predictions: List[PredictionResponse] = Field(..., description="Liste des prédictions")
    total_predictions: int = Field(..., description="Nombre total de prédictions")
    processing_time_ms: float = Field(..., description="Temps de traitement en millisecondes")

    class Config:
        json_schema_extra = {
            "example": {
                "predictions": [
                    {
                        "prediction": 2,
                        "prediction_label": "LONG",
                        "probabilities": {"SHORT": 0.15, "NEUTRAL": 0.25, "LONG": 0.60},
                        "confidence": 0.60,
                        "model_version": "1",
                        "timestamp": "2024-01-21T16:00:00"
                    }
                ],
                "total_predictions": 1,
                "processing_time_ms": 25.5
            }
        }


class ModelInfo(BaseModel):
    """
    Informations sur le modèle chargé
    """
    model_name: str = Field(..., description="Nom du modèle")
    model_version: Optional[str] = Field(None, description="Version du modèle")
    model_stage: Optional[str] = Field(None, description="Stage du modèle (Production, Staging, None)")
    run_id: Optional[str] = Field(None, description="MLflow run ID")
    loaded_at: Optional[datetime] = Field(None, description="Date de chargement du modèle")
    input_features: Optional[List[str]] = Field(None, description="Liste des features requises")
    n_features: Optional[int] = Field(None, description="Nombre de features")
    model_type: Optional[str] = Field(None, description="Type de modèle (LightGBM, etc.)")

    class Config:
        json_schema_extra = {
            "example": {
                "model_name": "OrionTrader_LightGBM_Classifier",
                "model_version": "1",
                "model_stage": "Production",
                "run_id": "abc123def456",
                "loaded_at": "2024-01-21T15:00:00",
                "input_features": ["close", "volatility_1h", "momentum_15m"],
                "n_features": 50,
                "model_type": "LightGBM"
            }
        }


class ModelMetrics(BaseModel):
    """
    Métriques du modèle
    """
    balanced_accuracy: Optional[float] = Field(None, description="Balanced Accuracy")
    macro_f1: Optional[float] = Field(None, description="Macro F1 Score")
    accuracy: Optional[float] = Field(None, description="Accuracy")
    metrics: Optional[Dict[str, Any]] = Field(None, description="Autres métriques")

    class Config:
        json_schema_extra = {
            "example": {
                "balanced_accuracy": 0.65,
                "macro_f1": 0.62,
                "accuracy": 0.68,
                "metrics": {
                    "overfitting": 0.05,
                    "backtest_sharpe_ratio": 1.5
                }
            }
        }
