"""
Router Monitoring - Endpoints pour le monitoring du modèle ML
Expose les métriques Prometheus (format texte) et les statistiques JSON
"""

from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.core.stats import get_stats

router = APIRouter()


@router.get(
    "/metrics",
    include_in_schema=False,
    summary="Métriques Prometheus (scraping)"
)
def prometheus_metrics():
    """
    Endpoint de scraping Prometheus

    Retourne toutes les métriques au format texte Prometheus.
    Utilisé par Prometheus pour la collecte automatique des métriques.

    **Ne pas appeler manuellement** — configuré dans prometheus.yml
    """
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/stats", summary="Statistiques de monitoring en temps réel")
def monitoring_stats():
    """
    Statistiques de monitoring en temps réel (format JSON)

    Retourne un résumé lisible de l'état courant du modèle en production :

    - **predictions** : total, répartition par classe, erreurs
    - **performance** : confiance moyenne, latence moyenne et p95
    - **cache** : hits/misses et taux de cache
    - **model** : rechargements, dernière prédiction, version active

    **Use case** : Dashboard Streamlit, debug, vérification rapide
    """
    return get_stats()


@router.get("/drift", summary="Détection du drift de distribution")
def drift_detection():
    """
    Détection du drift basée sur la distribution des prédictions

    Compare la distribution observée des classes (SHORT/NEUTRAL/LONG)
    à une distribution équilibrée attendue (~33% chacune).

    Une alerte est levée si une classe dépasse ±20% d'écart (sur 50+ prédictions).

    **Niveaux de sévérité :**
    - `medium` : écart entre 20% et 30%
    - `high` : écart supérieur à 30%

    **Use case** : Détection de data drift, dégradation du modèle, biais de prédiction
    """
    stats = get_stats()
    distribution = stats["predictions"]["distribution"]
    total = stats["predictions"]["total"]

    expected = round(1 / 3, 3)
    drift_alerts = []

    if total >= 50:
        for label, ratio in distribution.items():
            deviation = abs(ratio - expected)
            if deviation > 0.2:
                drift_alerts.append({
                    "class": label,
                    "expected": expected,
                    "observed": ratio,
                    "deviation": round(deviation, 3),
                    "severity": "high" if deviation > 0.3 else "medium",
                })

    return {
        "total_predictions": total,
        "distribution": distribution,
        "drift_detected": len(drift_alerts) > 0,
        "alerts": drift_alerts,
        "status": "warning" if drift_alerts else ("healthy" if total >= 50 else "insufficient_data"),
        "note": f"Minimum 50 prédictions requises pour la détection (actuellement {total})" if total < 50 else None,
    }
