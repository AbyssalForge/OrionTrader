# Installation de pyarrow dans le container Airflow

## Méthode 1 : Rebuild du container (RECOMMANDÉ)

```bash
# Arrêter les containers
docker-compose down

# Rebuild le container airflow avec les nouveaux requirements
docker-compose build airflow

# Redémarrer
docker-compose up -d
```

## Méthode 2 : Installation directe dans le container (temporaire)

Si vous voulez tester rapidement sans rebuild :

```bash
# Installer pyarrow dans le container airflow en cours d'exécution
docker exec -it orion_airflow pip install pyarrow

# Redémarrer le container pour prendre en compte
docker restart orion_airflow
```

## Vérification

Après installation, vérifiez que pyarrow est installé :

```bash
docker exec -it orion_airflow pip show pyarrow
```

## Résultat attendu

Après installation, votre DAG devrait :
- ✅ Récupérer 7/9 actifs depuis Stooq (EUR/USD, GBP/USD, USD/JPY, S&P 500, Dow Jones, Gold, Silver)
- ⚠️ Ignorer DXY et VIX (symboles non disponibles sur Stooq)
- ✅ Sauvegarder les 7 actifs en parquet sans erreur
