"""
Router Model - Endpoints pour prédictions ML avec MLflow
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
import mlflow
import numpy as np
import pandas as pd
import time
import os
from datetime import datetime, timedelta

from app.schemas.model import (
    SimplePredictionRequest,
    BatchPredictionRequest,
    PredictionResponse,
    BatchPredictionResponse,
    ModelInfo,
    ModelMetrics
)
from app.core.metrics import (
    track_prediction_metrics,
    update_model_info,
    track_model_reload,
    track_cache_hit,
    track_cache_miss,
    prediction_errors
)
from app.core import stats as monitoring_stats
from app.core.auth import verify_api_token
from app.models.api_token import APIToken
from app.core.database import get_db_context
from models import MT5EURUSDM15, YahooFinanceDaily, MarketSnapshotM15

router = APIRouter()

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5001")
MODEL_NAME = "classification_model"

_model_cache = {
    "model": None,
    "version": None,
    "loaded_at": None,
    "features": None
}


def get_historical_data(current_time: Optional[datetime] = None, lookback_periods: int = 50) -> pd.DataFrame:
    """
    Récupère l'historique des dernières bougies M15 depuis la BDD

    Args:
        current_time: Timestamp de référence (par défaut: maintenant)
        lookback_periods: Nombre de périodes à récupérer (par défaut: 50 pour MA50)

    Returns:
        DataFrame avec l'historique OHLCV + features micro
    """
    if current_time is None:
        current_time = datetime.now()

    try:
        with get_db_context() as db:
            # Récupérer les dernières bougies
            historical_data = db.query(MT5EURUSDM15)\
                .filter(MT5EURUSDM15.time <= current_time)\
                .order_by(MT5EURUSDM15.time.desc())\
                .limit(lookback_periods)\
                .all()

            if not historical_data:
                # Pas de données historiques, retourner un DataFrame vide
                return pd.DataFrame()

            # Convertir en DataFrame
            df = pd.DataFrame([{
                'time': row.time,
                'open': row.open,
                'high': row.high,
                'low': row.low,
                'close': row.close,
                'tick_volume': row.tick_volume,
                'close_diff': row.close_diff,
                'close_return': row.close_return,
                'high_low_range': row.high_low_range,
                'volatility_1h': row.volatility_1h,
                'volatility_4h': row.volatility_4h,
                'momentum_15m': row.momentum_15m,
                'momentum_1h': row.momentum_1h,
                'momentum_4h': row.momentum_4h,
                'body': row.body,
                'upper_shadow': row.upper_shadow,
                'lower_shadow': row.lower_shadow,
            } for row in historical_data])

            # Trier par ordre chronologique
            df = df.sort_values('time').reset_index(drop=True)

            return df

    except Exception as e:
        print(f"Erreur lors de la récupération de l'historique: {e}")
        return pd.DataFrame()


def compute_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule toutes les features techniques comme dans l'entraînement

    Args:
        df: DataFrame avec colonnes OHLCV + features micro

    Returns:
        DataFrame enrichi avec features techniques (MA, RSI, BB, etc.)
    """
    if df.empty or len(df) < 2:
        return df

    df = df.copy()

    # Features temporelles
    df['hour'] = pd.to_datetime(df['time']).dt.hour
    df['day_of_week'] = pd.to_datetime(df['time']).dt.dayofweek

    # Moyennes mobiles avec shift(1) pour éviter le leakage
    for window in [5, 10, 20, 50]:
        if len(df) >= window:
            df[f'ma_{window}'] = df['close'].rolling(window).mean().shift(1)

    # Distance aux MA (utilise les MA déjà shiftées)
    if 'ma_5' in df.columns:
        df['dist_ma_5'] = (df['close'] - df['ma_5']) / df['ma_5'] * 100
    if 'ma_20' in df.columns:
        df['dist_ma_20'] = (df['close'] - df['ma_20']) / df['ma_20'] * 100

    # Trends (utilise les MA déjà shiftées)
    if 'ma_5' in df.columns and 'ma_10' in df.columns:
        df['trend_short'] = (df['ma_5'] > df['ma_10']).astype(int)
    if 'ma_20' in df.columns and 'ma_50' in df.columns:
        df['trend_long'] = (df['ma_20'] > df['ma_50']).astype(int)

    # RSI
    if len(df) >= 14:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = (100 - (100 / (1 + rs))).shift(1)

    # Bollinger Bands
    if len(df) >= 20:
        bb_mid_temp = df['close'].rolling(20).mean()
        bb_std_temp = df['close'].rolling(20).std()
        df['bb_mid'] = bb_mid_temp.shift(1)
        df['bb_std'] = bb_std_temp.shift(1)
        df['bb_upper'] = df['bb_mid'] + (2 * df['bb_std'])
        df['bb_lower'] = df['bb_mid'] - (2 * df['bb_std'])
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

    # Lag features
    for lag in [1, 2, 3]:
        if 'close_return' in df.columns:
            df[f'close_return_lag_{lag}'] = df['close_return'].shift(lag)
        if 'momentum_1h' in df.columns:
            df[f'momentum_1h_lag_{lag}'] = df['momentum_1h'].shift(lag)

    return df


def get_model(version: Optional[str] = None, stage: Optional[str] = None):
    """
    Charge le modèle depuis MLflow Model Registry

    Args:
        version: Version spécifique du modèle (ex: "1", "2")
        stage: Stage du modèle ("Production", "Staging", "None")

    Returns:
        Modèle chargé
    """
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    if version:
        model_uri = f"models:/{MODEL_NAME}/{version}"
    elif stage:
        model_uri = f"models:/{MODEL_NAME}/{stage}"
    else:
        model_uri = f"models:/{MODEL_NAME}/latest"

    try:
        model = mlflow.pyfunc.load_model(model_uri)
        return model
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Modèle non trouvé: {MODEL_NAME}. Erreur: {str(e)}"
        )


def load_model_with_cache(version: Optional[str] = None, stage: Optional[str] = None):
    """
    Charge le modèle avec mise en cache
    """
    cache_key = version or stage or "latest"

    if _model_cache["model"] is not None and _model_cache["version"] == cache_key:
        track_cache_hit()
        monitoring_stats.update_cache(hit=True)
        return _model_cache["model"]

    track_cache_miss()
    monitoring_stats.update_cache(hit=False)
    model = get_model(version, stage)

    _model_cache["model"] = model
    _model_cache["version"] = cache_key
    _model_cache["loaded_at"] = datetime.now()

    update_model_info(MODEL_NAME, cache_key)

    return model


def transform_raw_to_features(data: SimplePredictionRequest) -> dict:
    """
    Transforme les données brutes en features comme dans l'ETL

    Récupère l'historique depuis la BDD et calcule toutes les features techniques:
    - Moyennes mobiles (MA5, MA10, MA20, MA50)
    - RSI
    - Bollinger Bands
    - Features temporelles
    - Lag features
    - Features macro (SPX, DXY, VIX, etc.)
    """
    try:
        # 1. Récupérer l'historique depuis la BDD
        df_hist = get_historical_data(lookback_periods=50)

        # 2. Créer la ligne actuelle avec les données de la requête
        current_row = {
            'time': datetime.now(),
            'open': data.open,
            'high': data.high,
            'low': data.low,
            'close': data.close,
            'tick_volume': data.tick_volume,
            'close_diff': data.close - data.open,
            'close_return': (data.close - data.open) / data.open if data.open != 0 else 0,
            'high_low_range': data.high - data.low,
        }

        # Calcul volatilité
        high_low_range = data.high - data.low
        current_row['volatility_1h'] = high_low_range / data.close if data.close != 0 else 0
        current_row['volatility_4h'] = current_row['volatility_1h'] * 1.5

        # Calcul momentum
        current_row['momentum_15m'] = current_row['close_return']
        current_row['momentum_1h'] = current_row['close_return'] * 2
        current_row['momentum_4h'] = current_row['close_return'] * 3

        # Analyse chandelier
        body = abs(data.close - data.open)
        upper_shadow = data.high - max(data.open, data.close)
        lower_shadow = min(data.open, data.close) - data.low
        current_row['body'] = body
        current_row['upper_shadow'] = upper_shadow
        current_row['lower_shadow'] = lower_shadow

        # 3. Ajouter la ligne actuelle à l'historique
        if not df_hist.empty:
            df = pd.concat([df_hist, pd.DataFrame([current_row])], ignore_index=True)
        else:
            # Pas d'historique, utiliser seulement la ligne actuelle
            df = pd.DataFrame([current_row])

        # 4. Calculer toutes les features techniques (MA, RSI, BB, etc.)
        df = compute_technical_features(df)

        # 5. Extraire les features de la dernière ligne (ligne actuelle)
        last_row = df.iloc[-1]
        features = last_row.to_dict()

        # 6. Ajouter les features macro (Yahoo, DXY, VIX, etc.)
        features['spx_close'] = data.spx_close if data.spx_close is not None else 4500.0
        features['spx_trend'] = data.spx_trend if data.spx_trend is not None else 0.0
        features['risk_on'] = data.risk_on if data.risk_on is not None else 0.5

        features['gold_close'] = data.gold_close if data.gold_close is not None else 2000.0
        features['gold_trend'] = data.gold_trend if data.gold_trend is not None else 0.0
        features['safe_haven'] = data.safe_haven if data.safe_haven is not None else 0.5

        features['dxy_close'] = data.dxy_close if data.dxy_close is not None else 104.0
        features['dxy_trend_1h'] = data.dxy_trend_1h if data.dxy_trend_1h is not None else 0.0
        features['dxy_trend_4h'] = data.dxy_trend_4h if data.dxy_trend_4h is not None else 0.0

        features['us10y_close'] = data.us10y_close if data.us10y_close is not None else 4.5
        features['us10y_trend'] = data.us10y_trend if data.us10y_trend is not None else 0.0

        vix = data.vix_close if data.vix_close is not None else 15.0
        features['vix_close'] = vix
        features['vix_spike'] = data.vix_spike if data.vix_spike is not None else 0.0
        features['market_stress'] = 1.0 if vix > 20.0 else 0.0

        # DXY strength
        dxy_trend_4h = data.dxy_trend_4h if data.dxy_trend_4h is not None else 0.0
        features['dxy_strength'] = dxy_trend_4h

        # Signal composite
        cr = features.get('close_return', 0.0)
        dxy_bias = -1.0 if dxy_trend_4h > 0.2 else (1.0 if dxy_trend_4h < -0.2 else 0.0)
        momentum_bias = 1.0 if cr > 0 else (-1.0 if cr < 0 else 0.0)
        features['macro_micro_aligned'] = 1.0 if dxy_bias == momentum_bias else 0.0
        features['trend_strength_composite'] = (momentum_bias + dxy_bias) / 2.0
        features['signal_confidence_score'] = min(abs(cr) * 100, 1.0)
        features['signal_divergence_count'] = 0 if dxy_bias == momentum_bias else 1
        features['euro_strength_bias'] = momentum_bias

        # Features par défaut pour celles qui manquent
        default_features = {
            'gdp_growth': 2.0,
            'unemployment': 4.0,
            'inflation': 3.0,
            'policy_rate': 5.0,
            'regime': 0,
            'volatility_regime': 1,
            'trend_regime': 0,
            'sentiment': 0.0,
            'stress': 0.0,
            'composite_signal': 0.0,
            'signal_strength': 0.5,
            'confidence_score': 0.5,
            'signal_coherence': 0.5,
            'event_window': 0,
            'event_window_active': 0,
            'high_impact_event': 0,
            'economic_surprise': 0.0,
            'vix_level': 0.0,
            'vix_change': 0.0,
        }

        for key, value in default_features.items():
            if key not in features:
                features[key] = value

        # Ratios chandelier
        total_range = high_low_range if high_low_range != 0 else 1
        features['body_ratio'] = body / total_range
        features['upper_shadow_ratio'] = upper_shadow / total_range
        features['lower_shadow_ratio'] = lower_shadow / total_range

        features['bullish_candle'] = 1.0 if data.close > data.open else 0.0
        features['bearish_candle'] = 1.0 if data.close < data.open else 0.0
        features['is_high_volatility'] = 1.0 if features.get('volatility_1h', 0) > 0.002 else 0.0

        # Convertir les valeurs NaN en 0.0
        for key in features:
            if isinstance(features[key], (float, np.floating)) and np.isnan(features[key]):
                features[key] = 0.0

        return features

    except Exception as e:
        print(f"Erreur dans transform_raw_to_features: {e}")
        # Fallback: utiliser l'ancienne méthode sans historique
        return transform_raw_to_features_fallback(data)


def transform_raw_to_features_fallback(data: SimplePredictionRequest) -> dict:
    """
    Version fallback sans historique (utilisée si la BDD est inaccessible)
    """
    features = {}
    features['open'] = data.open
    features['high'] = data.high
    features['low'] = data.low
    features['tick_volume'] = data.tick_volume
    features['close_diff'] = data.close - data.open
    features['close_return'] = (data.close - data.open) / data.open if data.open != 0 else 0
    features['high_low_range'] = data.high - data.low

    # Features de base seulement
    high_low_range = data.high - data.low
    features['volatility_1h'] = high_low_range / data.close if data.close != 0 else 0
    features['volatility_4h'] = features['volatility_1h'] * 1.5
    features['momentum_15m'] = features['close_return']
    features['momentum_1h'] = features['close_return'] * 2
    features['momentum_4h'] = features['close_return'] * 3

    body = abs(data.close - data.open)
    upper_shadow = data.high - max(data.open, data.close)
    lower_shadow = min(data.open, data.close) - data.low
    features['body'] = body
    features['upper_shadow'] = upper_shadow
    features['lower_shadow'] = lower_shadow

    # Toutes les autres features à 0 ou valeur par défaut
    features['spx_close'] = data.spx_close if data.spx_close is not None else 4500.0
    features['dxy_close'] = data.dxy_close if data.dxy_close is not None else 104.0
    features['vix_close'] = data.vix_close if data.vix_close is not None else 15.0

    return features


def format_prediction_response(prediction: int, probabilities: np.ndarray, version: Optional[str] = None) -> PredictionResponse:
    """
    Formate la réponse de prédiction
    """
    class_labels = {0: "SHORT", 1: "NEUTRAL", 2: "LONG"}

    prob_dict = {
        "SHORT": float(probabilities[0]),
        "NEUTRAL": float(probabilities[1]),
        "LONG": float(probabilities[2])
    }

    return PredictionResponse(
        prediction=int(prediction),
        prediction_label=class_labels[int(prediction)],
        probabilities=prob_dict,
        confidence=float(np.max(probabilities)),
        model_version=version,
        timestamp=datetime.now()
    )



@router.post("/predict", response_model=PredictionResponse)
def predict(
    request: SimplePredictionRequest,
    version: Optional[str] = Query(None, description="Version du modèle (ex: '1', '2')"),
    stage: Optional[str] = Query(None, description="Stage du modèle ('Production', 'Staging')"),
    token: APIToken = Depends(verify_api_token)
):
    """
    Prédiction avec données brutes

    Effectue une prédiction en fournissant uniquement les données de base (OHLCV).
    Toutes les features complexes sont calculées automatiquement comme dans l'ETL.

    **Entrées requises:**
    - open, high, low, close, tick_volume (données de la bougie)

    **Entrées optionnelles:**
    - Indicateurs externes (SPX, Gold, DXY, VIX, etc.)
    - Si non fournis, des valeurs par défaut neutres sont utilisées

    **Classes de sortie:**
    - 0 = SHORT (vendre)
    - 1 = NEUTRAL (ne rien faire)
    - 2 = LONG (acheter)

    **Use case:** Trading en temps réel avec données brutes uniquement
    """
    try:
        start_time = time.time()
        model = load_model_with_cache(version, stage)

        features_dict = transform_raw_to_features(request)

        try:
            client = mlflow.tracking.MlflowClient()
            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

            if version:
                model_version = client.get_model_version(MODEL_NAME, version)
            else:
                versions = client.search_model_versions(f"name='{MODEL_NAME}'")
                if versions:
                    model_version = versions[0]
                else:
                    raise Exception("Aucune version de modèle trouvée")

            try:
                features_path = client.download_artifacts(model_version.run_id, "features.txt")
                with open(features_path, 'r') as f:
                    feature_names = [line.strip() for line in f.readlines()]
            except:
                feature_names = sorted(features_dict.keys())

        except Exception as e:
            feature_names = sorted(features_dict.keys())

        features_array = np.array([[features_dict.get(f, 0.0) for f in feature_names]])

        prediction_raw = model.predict(features_array)
        if isinstance(prediction_raw, np.ndarray):
            if len(prediction_raw.shape) > 1:
                prediction = int(prediction_raw[0][0])
            else:
                prediction = int(prediction_raw[0])
        else:
            prediction = int(prediction_raw)

        try:
            prob_array = model.predict_proba(features_array)
            if len(prob_array.shape) > 1:
                probabilities = prob_array[0]
            else:
                probabilities = prob_array
        except (AttributeError, Exception):
            probabilities = np.array([0.33, 0.34, 0.33])
            probabilities[int(prediction)] = 1.0

        response = format_prediction_response(prediction, probabilities, version or stage)
        track_prediction_metrics(prediction, response.probabilities, version or stage)

        latency_ms = (time.time() - start_time) * 1000
        monitoring_stats.update_prediction(
            prediction_label=response.prediction_label,
            confidence=response.confidence,
            latency_ms=latency_ms,
            version=version or stage,
        )

        return response

    except Exception as e:
        prediction_errors.labels(error_type=type(e).__name__).inc()
        monitoring_stats.update_error()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la prédiction: {str(e)}")


@router.post("/predict/batch", response_model=BatchPredictionResponse)
def predict_batch(
    request: BatchPredictionRequest,
    version: Optional[str] = Query(None, description="Version du modèle"),
    stage: Optional[str] = Query(None, description="Stage du modèle"),
    token: APIToken = Depends(verify_api_token)
):
    """
    Prédictions en batch avec données brutes

    Effectue plusieurs prédictions en une seule requête pour de meilleures performances.
    Accepte une liste de données OHLCV brutes qui seront transformées automatiquement.

    **Use case:** Backtesting, analyse historique, prédictions multiples
    """
    try:
        start_time = time.time()

        model = load_model_with_cache(version, stage)

        try:
            client = mlflow.tracking.MlflowClient()
            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

            if version:
                model_version = client.get_model_version(MODEL_NAME, version)
            else:
                versions = client.search_model_versions(f"name='{MODEL_NAME}'")
                if versions:
                    model_version = versions[0]
                else:
                    raise Exception("Aucune version de modèle trouvée")

            try:
                features_path = client.download_artifacts(model_version.run_id, "features.txt")
                with open(features_path, 'r') as f:
                    feature_names = [line.strip() for line in f.readlines()]
            except:
                feature_names = None

        except Exception:
            feature_names = None

        predictions = []

        for raw_data in request.predictions:
            features_dict = transform_raw_to_features(raw_data)

            if feature_names is None:
                feature_names = sorted(features_dict.keys())

            features_array = np.array([[features_dict.get(f, 0.0) for f in feature_names]])

            prediction_raw = model.predict(features_array)
            if isinstance(prediction_raw, np.ndarray):
                if len(prediction_raw.shape) > 1:
                    prediction = int(prediction_raw[0][0])
                else:
                    prediction = int(prediction_raw[0])
            else:
                prediction = int(prediction_raw)

            try:
                prob_array = model.predict_proba(features_array)
                if len(prob_array.shape) > 1:
                    probabilities = prob_array[0]
                else:
                    probabilities = prob_array
            except (AttributeError, Exception):
                probabilities = np.array([0.33, 0.34, 0.33])
                probabilities[int(prediction)] = 1.0

            response = format_prediction_response(prediction, probabilities, version or stage)
            track_prediction_metrics(prediction, response.probabilities, version or stage)
            predictions.append(response)

        processing_time = (time.time() - start_time) * 1000  # en ms

        return BatchPredictionResponse(
            predictions=predictions,
            total_predictions=len(predictions),
            processing_time_ms=processing_time
        )

    except Exception as e:
        prediction_errors.labels(error_type=type(e).__name__).inc()
        raise HTTPException(status_code=500, detail=f"Erreur lors des prédictions batch: {str(e)}")


@router.get("/info", response_model=ModelInfo)
def get_model_info(
    version: Optional[str] = Query(None, description="Version du modèle"),
    stage: Optional[str] = Query(None, description="Stage du modèle"),
    token: APIToken = Depends(verify_api_token)
):
    """
    Informations sur le modèle chargé

    Retourne les métadonnées du modèle, y compris:
    - Nom et version
    - Date de chargement
    - Features requises par l'API (OHLCV + indicateurs optionnels)
    - Type de modèle

    **Note:** Les features affichées sont celles requises par l'API REST.
    Le modèle interne utilise 61 features qui sont calculées automatiquement.

    **Use case:** Debugging, monitoring, documentation
    """
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    try:
        client = mlflow.tracking.MlflowClient()

        if version:
            model_version = client.get_model_version(MODEL_NAME, version)
        else:
            versions = client.search_model_versions(f"name='{MODEL_NAME}'")
            if not versions:
                raise HTTPException(status_code=404, detail=f"Aucune version trouvée pour le modèle {MODEL_NAME}")
            model_version = versions[0]

        run = client.get_run(model_version.run_id)

        input_features = [
            "open (required)",
            "high (required)",
            "low (required)",
            "close (required)",
            "tick_volume (required)",
            "spx_close (optional)",
            "spx_trend (optional)",
            "risk_on (optional)",
            "gold_close (optional)",
            "gold_trend (optional)",
            "safe_haven (optional)",
            "dxy_close (optional)",
            "dxy_trend_1h (optional)",
            "dxy_trend_4h (optional)",
            "us10y_close (optional)",
            "us10y_trend (optional)",
            "vix_close (optional)",
            "vix_spike (optional)"
        ]

        return ModelInfo(
            model_name=MODEL_NAME,
            model_version=model_version.version,
            model_stage=model_version.current_stage,
            run_id=model_version.run_id,
            loaded_at=_model_cache.get("loaded_at"),
            input_features=input_features,
            n_features=len(input_features),
            model_type="LightGBM"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des infos: {str(e)}")


@router.get("/metrics", response_model=ModelMetrics)
def get_model_metrics(
    version: Optional[str] = Query(None, description="Version du modèle"),
    token: APIToken = Depends(verify_api_token)
):
    """
    Métriques du modèle

    Retourne les métriques d'entraînement du modèle:
    - Balanced Accuracy
    - Macro F1 Score
    - Accuracy
    - Autres métriques (overfitting, Sharpe ratio, etc.)

    **Use case:** Évaluation de la qualité du modèle, comparaison de versions
    """
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    try:
        client = mlflow.tracking.MlflowClient()

        if version:
            model_version = client.get_model_version(MODEL_NAME, version)
        else:
            versions = client.search_model_versions(f"name='{MODEL_NAME}'")
            if not versions:
                raise HTTPException(status_code=404, detail=f"Aucune version trouvée pour le modèle {MODEL_NAME}")
            model_version = versions[0]

        run = client.get_run(model_version.run_id)
        metrics = run.data.metrics

        return ModelMetrics(
            balanced_accuracy=metrics.get('best_balanced_accuracy'),
            macro_f1=metrics.get('best_macro_f1'),
            accuracy=metrics.get('best_accuracy'),
            metrics={
                k: v for k, v in metrics.items()
                if k not in ['best_balanced_accuracy', 'best_macro_f1', 'best_accuracy']
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des métriques: {str(e)}")


@router.post("/reload")
def reload_model(
    version: Optional[str] = Query(None, description="Version du modèle à charger"),
    stage: Optional[str] = Query(None, description="Stage du modèle à charger"),
    token: APIToken = Depends(verify_api_token)
):
    """
    Recharge le modèle

    Force le rechargement du modèle depuis MLflow (vide le cache).

    **Use case:** Après mise à jour du modèle, pour charger une nouvelle version
    """
    try:
        _model_cache["model"] = None
        _model_cache["version"] = None
        _model_cache["loaded_at"] = None

        model = load_model_with_cache(version, stage)

        track_model_reload()
        monitoring_stats.update_reload()

        return {
            "status": "success",
            "message": f"Modèle {MODEL_NAME} rechargé avec succès",
            "version": version or stage or "latest",
            "loaded_at": _model_cache["loaded_at"]
        }

    except Exception as e:
        prediction_errors.labels(error_type=type(e).__name__).inc()
        raise HTTPException(status_code=500, detail=f"Erreur lors du rechargement: {str(e)}")
