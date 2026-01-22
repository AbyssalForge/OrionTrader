# 📊 Monitoring OrionTrader ML Model

Ce guide explique comment utiliser le système de monitoring Prometheus + Grafana pour surveiller les performances du modèle ML en temps réel.

## 🚀 Démarrage rapide

### 1. Rebuild et démarrer les conteneurs

```bash
# Rebuild FastAPI avec les nouvelles dépendances Prometheus
docker-compose up -d --build fastapi

# Redémarrer Prometheus et Grafana
docker-compose restart prometheus grafana
```

### 2. Accéder aux interfaces

- **Grafana**: http://localhost:3000
  - Username: `admin`
  - Password: `admin`

- **Prometheus**: http://localhost:9090

- **Métriques FastAPI**: http://localhost:8000/metrics

## 📈 Dashboard Grafana

Le dashboard **"OrionTrader ML Monitoring"** est automatiquement provisionné et contient :

### Métriques principales

1. **Prédictions par classe** (rate/min)
   - Taux de prédictions SHORT, NEUTRAL, LONG par minute
   - Permet de détecter les déséquilibres dans les prédictions

2. **Confiance moyenne** (p95)
   - Percentile 95 de la confiance des prédictions
   - Seuils : 🔴 <50% | 🟡 50-70% | 🟢 >70%

3. **Latence de prédiction** (p95)
   - Temps de traitement des prédictions
   - Seuils : 🟢 <0.5s | 🟡 0.5-1s | 🔴 >1s

4. **Distribution des prédictions**
   - Nombre total de prédictions par classe
   - Graphique en barres cumulé

5. **Probabilités moyennes**
   - Évolution des probabilités moyennes pour chaque classe
   - Utile pour détecter le drift du modèle

6. **Erreurs de prédiction**
   - Taux d'erreurs par type (rate/5m)
   - Permet de détecter les problèmes rapidement

7. **Cache Hit Rate**
   - Ratio de hits/misses du cache du modèle
   - Indicateur de performance du système

8. **Model Reloads**
   - Nombre de fois où le modèle a été rechargé
   - Utile pour suivre les mises à jour

## 🎯 Métriques Prometheus disponibles

### Métriques personnalisées ML

```promql
# Nombre total de prédictions par classe
model_predictions_total{prediction_label="SHORT|NEUTRAL|LONG", model_version="1"}

# Distribution de la confiance des prédictions
model_prediction_confidence_bucket

# Temps de traitement des prédictions
model_prediction_duration_seconds_bucket{endpoint="predict_single|predict_batch"}

# Erreurs de prédiction
model_prediction_errors_total{error_type="HTTPException|ValueError|..."}

# Nombre de features utilisées
model_features_count

# Probabilités moyennes par classe
model_avg_probability_short
model_avg_probability_neutral
model_avg_probability_long

# Cache du modèle
model_cache_hits_total
model_cache_misses_total

# Rechargements du modèle
model_reload_total
```

### Métriques FastAPI automatiques

```promql
# Requêtes HTTP totales
http_requests_total{method="POST", handler="/model/predict"}

# Durée des requêtes HTTP
http_request_duration_seconds_bucket

# Requêtes en cours
http_requests_inprogress
```

## 📊 Exemples de requêtes PromQL

### Taux de prédictions par classe (dernière minute)
```promql
rate(model_predictions_total[1m])
```

### Latence p95 des prédictions
```promql
histogram_quantile(0.95, rate(model_prediction_duration_seconds_bucket[5m]))
```

### Taux d'erreur
```promql
rate(model_prediction_errors_total[5m])
```

### Confiance moyenne
```promql
histogram_quantile(0.5, rate(model_prediction_confidence_bucket[5m]))
```

### Distribution des prédictions (pourcentage)
```promql
sum(model_predictions_total) by (prediction_label)
/
sum(model_predictions_total) * 100
```

### Cache hit rate
```promql
model_cache_hits_total / (model_cache_hits_total + model_cache_misses_total)
```

## 🔔 Alertes recommandées

Créez ces alertes dans Prometheus pour être notifié des problèmes :

### 1. Latence élevée
```yaml
- alert: HighPredictionLatency
  expr: histogram_quantile(0.95, rate(model_prediction_duration_seconds_bucket[5m])) > 1
  for: 5m
  annotations:
    summary: "Latence de prédiction élevée (p95 > 1s)"
```

### 2. Taux d'erreur élevé
```yaml
- alert: HighErrorRate
  expr: rate(model_prediction_errors_total[5m]) > 0.1
  for: 5m
  annotations:
    summary: "Taux d'erreur de prédiction élevé (>10%)"
```

### 3. Confiance faible
```yaml
- alert: LowPredictionConfidence
  expr: histogram_quantile(0.95, rate(model_prediction_confidence_bucket[5m])) < 0.5
  for: 10m
  annotations:
    summary: "Confiance des prédictions faible (p95 < 50%)"
```

### 4. Déséquilibre des prédictions
```yaml
- alert: PredictionImbalance
  expr: |
    (
      max(sum(rate(model_predictions_total[10m])) by (prediction_label))
      /
      min(sum(rate(model_predictions_total[10m])) by (prediction_label))
    ) > 5
  for: 15m
  annotations:
    summary: "Déséquilibre important dans les prédictions (ratio >5)"
```

## 🔍 Détection de drift du modèle

Pour détecter si le modèle dérive :

1. **Surveiller les probabilités moyennes**
   - Si une classe domine constamment (>80%), le modèle pourrait dériver
   - Comparer avec les distributions d'entraînement

2. **Suivre la confiance**
   - Une baisse progressive de confiance peut indiquer un drift
   - Comparer avec les métriques de validation

3. **Analyser les features**
   - Vérifier que les valeurs d'entrée restent dans les plages attendues
   - Utiliser Evidently AI pour une analyse plus approfondie (recommandé)

## 🛠️ Troubleshooting

### Métriques non disponibles dans Grafana

1. Vérifier que FastAPI expose les métriques :
   ```bash
   curl http://localhost:8000/metrics
   ```

2. Vérifier que Prometheus collecte les données :
   - Aller sur http://localhost:9090/targets
   - Le job `fastapi` doit être "UP"

3. Vérifier les logs Prometheus :
   ```bash
   docker logs orion_prometheus
   ```

### Dashboard vide

1. Faire au moins une prédiction pour générer des métriques :
   ```bash
   curl -X POST http://localhost:8000/model/predict \
     -H "Content-Type: application/json" \
     -d '{
       "open": 1.0845,
       "high": 1.0855,
       "low": 1.0840,
       "close": 1.0850,
       "tick_volume": 1000
     }'
   ```

2. Vérifier la période de temps dans Grafana (en haut à droite)
   - Utiliser "Last 15 minutes" pour commencer

## 📚 Ressources

- [Documentation Prometheus](https://prometheus.io/docs/)
- [Documentation Grafana](https://grafana.com/docs/)
- [Prometheus FastAPI Instrumentator](https://github.com/trallnag/prometheus-fastapi-instrumentator)

## 🎓 Next Steps

Pour aller plus loin dans le monitoring ML :

1. **Evidently AI** : Détection automatique de drift
2. **MLflow Tracking** : Déjà en place, complémente Prometheus
3. **Alertmanager** : Système d'alerting avancé
4. **Loki** : Agrégation de logs (complète Prometheus)
5. **Jaeger** : Tracing distribué pour debugging
