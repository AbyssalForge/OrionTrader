"""
Tracker d'état en mémoire pour le monitoring du modèle ML
Maintenu en parallèle des métriques Prometheus pour exposition JSON
"""

from collections import deque
from datetime import datetime
from threading import Lock

_lock = Lock()

_stats = {
    "predictions": {
        "total": 0,
        "by_class": {"SHORT": 0, "NEUTRAL": 0, "LONG": 0},
        "errors": 0,
    },
    "performance": {
        "recent_confidences": deque(maxlen=100),
        "recent_latencies_ms": deque(maxlen=100),
    },
    "cache": {
        "hits": 0,
        "misses": 0,
    },
    "model": {
        "reloads": 0,
        "last_prediction_at": None,
        "version": None,
    },
}


def update_prediction(prediction_label: str, confidence: float, latency_ms: float, version: str = None):
    with _lock:
        _stats["predictions"]["total"] += 1
        _stats["predictions"]["by_class"][prediction_label] = (
            _stats["predictions"]["by_class"].get(prediction_label, 0) + 1
        )
        _stats["performance"]["recent_confidences"].append(confidence)
        _stats["performance"]["recent_latencies_ms"].append(latency_ms)
        _stats["model"]["last_prediction_at"] = datetime.now().isoformat()
        if version:
            _stats["model"]["version"] = version


def update_error():
    with _lock:
        _stats["predictions"]["errors"] += 1


def update_cache(hit: bool):
    with _lock:
        if hit:
            _stats["cache"]["hits"] += 1
        else:
            _stats["cache"]["misses"] += 1


def update_reload():
    with _lock:
        _stats["model"]["reloads"] += 1


def get_stats() -> dict:
    with _lock:
        confidences = list(_stats["performance"]["recent_confidences"])
        latencies = list(_stats["performance"]["recent_latencies_ms"])
        total = _stats["predictions"]["total"]
        by_class = dict(_stats["predictions"]["by_class"])
        cache_hits = _stats["cache"]["hits"]
        cache_misses = _stats["cache"]["misses"]

        sorted_latencies = sorted(latencies)

        return {
            "predictions": {
                "total": total,
                "by_class": by_class,
                "distribution": {
                    k: round(v / total, 3) if total > 0 else 0.0
                    for k, v in by_class.items()
                },
                "errors": _stats["predictions"]["errors"],
                "error_rate": round(_stats["predictions"]["errors"] / max(total, 1), 3),
            },
            "performance": {
                "avg_confidence": round(sum(confidences) / len(confidences), 3) if confidences else None,
                "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
                "p95_latency_ms": (
                    round(sorted_latencies[int(len(sorted_latencies) * 0.95)], 1)
                    if len(sorted_latencies) >= 20
                    else None
                ),
                "sample_size": len(confidences),
            },
            "cache": {
                "hits": cache_hits,
                "misses": cache_misses,
                "hit_rate": round(cache_hits / max(cache_hits + cache_misses, 1), 3),
            },
            "model": {
                "reloads": _stats["model"]["reloads"],
                "last_prediction_at": _stats["model"]["last_prediction_at"],
                "version": _stats["model"]["version"],
            },
        }
