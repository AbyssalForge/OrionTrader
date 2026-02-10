"""
Métriques Prometheus personnalisées pour le monitoring du modèle ML
"""

from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps


prediction_counter = Counter(
    'model_predictions_total',
    'Nombre total de prédictions par classe',
    ['prediction_label', 'model_version']
)

prediction_confidence = Histogram(
    'model_prediction_confidence',
    'Distribution de la confiance des prédictions',
    buckets=[0.0, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

prediction_duration = Histogram(
    'model_prediction_duration_seconds',
    'Temps de traitement des prédictions',
    ['endpoint']
)

prediction_errors = Counter(
    'model_prediction_errors_total',
    'Nombre d\'erreurs lors des prédictions',
    ['error_type']
)

model_features_count = Gauge(
    'model_features_count',
    'Nombre de features utilisées par le modèle'
)

model_info = Info(
    'model_loaded',
    'Informations sur le modèle actuellement chargé'
)

avg_probability_short = Gauge(
    'model_avg_probability_short',
    'Probabilité moyenne pour la classe SHORT (fenêtre glissante)'
)

avg_probability_neutral = Gauge(
    'model_avg_probability_neutral',
    'Probabilité moyenne pour la classe NEUTRAL (fenêtre glissante)'
)

avg_probability_long = Gauge(
    'model_avg_probability_long',
    'Probabilité moyenne pour la classe LONG (fenêtre glissante)'
)

model_reload_counter = Counter(
    'model_reload_total',
    'Nombre de fois où le modèle a été rechargé'
)

model_cache_hits = Counter(
    'model_cache_hits_total',
    'Nombre de fois où le modèle a été récupéré du cache'
)

model_cache_misses = Counter(
    'model_cache_misses_total',
    'Nombre de fois où le modèle n\'était pas en cache'
)



def track_prediction_time(endpoint_name: str):
    """
    Décorateur pour tracker le temps d'exécution des prédictions

    Usage:
        @track_prediction_time("predict_single")
        def predict(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                prediction_duration.labels(endpoint=endpoint_name).observe(duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                prediction_duration.labels(endpoint=endpoint_name).observe(duration)
                prediction_errors.labels(error_type=type(e).__name__).inc()
                raise
        return wrapper
    return decorator


def track_prediction_metrics(prediction: int, probabilities: dict, version: str = None):
    """
    Track les métriques d'une prédiction

    Args:
        prediction: Classe prédite (0=SHORT, 1=NEUTRAL, 2=LONG)
        probabilities: Dict des probabilités {"SHORT": 0.1, "NEUTRAL": 0.2, "LONG": 0.7}
        version: Version du modèle
    """
    class_labels = {0: "SHORT", 1: "NEUTRAL", 2: "LONG"}
    prediction_label = class_labels.get(prediction, "UNKNOWN")

    prediction_counter.labels(
        prediction_label=prediction_label,
        model_version=version or "unknown"
    ).inc()

    confidence = max(probabilities.values()) if probabilities else 0.0
    prediction_confidence.observe(confidence)

    if probabilities:
        avg_probability_short.set(probabilities.get("SHORT", 0.0))
        avg_probability_neutral.set(probabilities.get("NEUTRAL", 0.0))
        avg_probability_long.set(probabilities.get("LONG", 0.0))


def update_model_info(model_name: str, version: str, n_features: int = None):
    """
    Met à jour les informations sur le modèle chargé

    Args:
        model_name: Nom du modèle
        version: Version du modèle
        n_features: Nombre de features
    """
    model_info.info({
        'model_name': model_name,
        'version': version or 'unknown',
        'features_count': str(n_features) if n_features else 'unknown'
    })

    if n_features:
        model_features_count.set(n_features)


def track_model_reload():
    """Incrémente le compteur de rechargements du modèle"""
    model_reload_counter.inc()


def track_cache_hit():
    """Incrémente le compteur de cache hits"""
    model_cache_hits.inc()


def track_cache_miss():
    """Incrémente le compteur de cache misses"""
    model_cache_misses.inc()
