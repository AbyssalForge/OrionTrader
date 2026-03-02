# Grafana Dashboards - OrionTrader

Ce dossier contient les dashboards Grafana pré-configurés pour le monitoring du projet OrionTrader.

## 📊 Dashboards disponibles

### OrionTrader ML Monitoring (`ml_monitoring.json`)

**UID:** `oriontrader-ml`

Dashboard principal pour le monitoring du modèle de Machine Learning en production.

#### Panels inclus

**🎯 Métriques principales (Top Row)**
- **Confiance moyenne (P95)** - Gauge avec seuils (rouge < 50%, jaune < 70%, vert > 70%)
- **Latence prédiction (P95)** - Gauge avec seuils (vert < 0.5s, jaune < 1s, rouge > 1s)

**📈 Graphiques temporels**
- **Prédictions par classe (rate/min)** - Évolution du taux de prédictions SHORT/NEUTRAL/LONG
- **Distribution des prédictions (total)** - Nombre total de prédictions par classe (barres)
- **Probabilités moyennes par classe** - Évolution des probabilités moyennes (drift detection)
- **Erreurs de prédiction (rate/5m)** - Taux d'erreurs par type

**📊 Statistiques système**
- **Cache Hit Rate** - Efficacité du cache du modèle
- **Model Reloads** - Nombre de rechargements du modèle
- **Requêtes API totales (rate/5m)** - Trafic API global
- **Features utilisées** - Nombre de features du modèle

#### Accès

```bash
# Démarrer Grafana
docker compose up grafana

# Accéder à l'interface
http://localhost:3000

# Identifiants par défaut
Username: admin
Password: admin
```

#### Configuration

Le dashboard est provisionné automatiquement via:
- `grafana/provisioning/dashboards/dashboard.yml` - Configuration de provisioning
- `docker-compose.yaml` - Volume mount du dashboard

#### Refresh

- **Auto-refresh:** 5 secondes
- **Période par défaut:** 15 dernières minutes

#### Datasource

- **Prometheus** - `http://prometheus:9090`
- Configuration automatique via `grafana/provisioning/datasources/`

---

## 🚨 Alertes Prometheus

Les alertes Prometheus sont définies dans `prometheus/alert.rules.yml`:

**Alertes disponibles:**
- `LowModelConfidence` - Confiance < 50% pendant 5min
- `HighPredictionErrorRate` - Taux d'erreur > 5%
- `ModelPredictionBias` - Biais vers une classe > 80%
- `SlowModelPrediction` - P95 > 1 seconde
- `CriticalModelPrediction` - P99 > 5 secondes
- `ProbabilityDistributionShift` - Drift de distribution > 20%
- `LowCacheHitRate` - Cache hit rate < 50%
- `FrequentModelReload` - Rechargements fréquents
- `NoModelPredictions` - Aucune prédiction depuis 10min
- `NoMetricsCollected` - Collecte interrompue

Visualiser les alertes: http://localhost:9090/alerts

---

## 🔧 Personnalisation

Pour modifier le dashboard:

1. **Via l'interface Grafana:**
   - Modifier le dashboard dans Grafana UI
   - Exporter le JSON (Share → Export → Save to file)
   - Remplacer `ml_monitoring.json`

2. **Via le fichier JSON:**
   - Éditer directement `ml_monitoring.json`
   - Redémarrer Grafana: `docker compose restart grafana`

---

## 📚 Documentation

- **Métriques Prometheus:** `fastapi/app/core/metrics.py`
- **Règles d'alerte:** `prometheus/alert.rules.yml`
- **Documentation complète:** `docs/COMPETENCES_MLOPS.md`
