# Protection Week-end dans le Pipeline ETL

## Résumé

Suite à la simplification de l'architecture (remplacement MT5/Pyro5 par Yahoo Finance), une protection automatique des week-ends a été implémentée pour éviter les erreurs d'extraction de données lorsque les marchés sont fermés.

## Problème Résolu

Lorsque l'utilisateur demandait des données sur un week-end (ex: 31 janvier - 1er février 2026), le pipeline échouait car:
- Yahoo Finance ne fournit pas de données intraday (15m) pour les week-ends
- Les marchés financiers sont fermés samedi et dimanche
- Les tentatives d'extraction retournaient des DataFrames vides, causant des erreurs dans les transformations

## Solution Implémentée

### 1. Module `airflow/utils/trading_calendar.py`

Nouveau module avec 4 fonctions utilitaires:

- **`is_trading_day(date)`**: Vérifie si une date est un jour de trading (lundi-vendredi)
- **`get_last_trading_day(date)`**: Retourne le dernier jour de trading avant ou égal à la date donnée
- **`adjust_date_range_for_trading(start, end)`**: Ajuste une plage de dates pour exclure les week-ends
- **`get_trading_days_info(start, end)`**: Fournit des informations détaillées sur les jours de trading dans une plage

### 2. Intégration dans le DAG ETL

Le fichier `airflow/dags/etl_forex_pipeline.py` a été modifié:

**Dates par défaut:**
```python
from utils.trading_calendar import get_last_trading_day

# Utilise automatiquement le dernier jour de trading
DEFAULT_DATE_END = get_last_trading_day(DEFAULT_DATE_NOW - timedelta(days=1))
DEFAULT_DATE_START = DEFAULT_DATE_END - timedelta(days=1)  # J-1 (jeudi si end=vendredi)
```

**Ajustement automatique des dates:**
```python
@task
def extract_yahoo(**context):
    # Récupérer les dates demandées par l'utilisateur
    start = datetime.strptime(start_str, '%Y-%m-%d')
    end = datetime.strptime(end_str, '%Y-%m-%d')

    # Ajuster automatiquement pour éviter les week-ends
    start_adjusted, end_adjusted = adjust_date_range_for_trading(start, end)

    # Afficher les ajustements si nécessaire
    if start != start_adjusted or end != end_adjusted:
        print(f"[YAHOO] ⚠️  Ajustement des dates (week-end détecté):")
        print(f"[YAHOO]    start: {start.date()} -> {start_adjusted.date()}")
        print(f"[YAHOO]    end:   {end.date()} -> {end_adjusted.date()}")

    # Extraire avec les dates ajustées
    return extract_yahoo_data(start=start_adjusted, end=end_adjusted)
```

## Tests et Validation

### Test 1: `test_trading_calendar.py`
Test unitaire des fonctions de calendrier:
- ✓ Détection des jours de semaine (lundi-vendredi) vs week-end (samedi-dimanche)
- ✓ Calcul du dernier jour de trading
- ✓ Ajustement de plages de dates
- ✓ Calcul des jours de trading sur une grande plage (2020-2022 = 523 jours de trading)

### Test 2: `test_weekend_protection.py`
Test de 5 scénarios réels d'utilisation du pipeline:

**Scénario 1:** Exécution le dimanche
- Résultat: Pipeline utilise automatiquement le vendredi précédent

**Scénario 2:** Demande samedi -> dimanche
- Résultat: Ajusté à vendredi -> vendredi

**Scénario 3:** Plage vendredi -> lundi
- Résultat: 2 jours de trading identifiés sur 4 jours totaux

**Scénario 4:** Grande plage 2020-2022
- Résultat: 523 jours de trading / 731 jours totaux (208 week-ends exclus)

**Scénario 5:** Dates par défaut du DAG
- Résultat: Utilise automatiquement les derniers jours de trading (J-1 -> J, ex: jeudi -> vendredi)

## Bénéfices

1. **Fiabilité:** Le pipeline ne peut plus échouer à cause de week-ends
2. **Automatique:** Pas besoin de vérifier manuellement les dates avant l'exécution
3. **Transparent:** Les ajustements sont loggés dans les sorties du DAG
4. **Flexible:** Fonctionne pour exécution manuelle ET automatique (schedule)
5. **Compatible:** Gère tous les cas (dates par défaut, dates manuelles, grandes plages)

## Fichiers Modifiés

- `airflow/utils/trading_calendar.py` (NOUVEAU)
- `airflow/dags/etl_forex_pipeline.py` (MODIFIÉ)
- `test_trading_calendar.py` (NOUVEAU)
- `test_weekend_protection.py` (NOUVEAU)

## Exemples d'Utilisation

### Exécution automatique quotidienne
```bash
# Le DAG s'exécute à 18h00 UTC tous les jours
# Si c'est samedi ou dimanche, il utilisera automatiquement le vendredi
```

### Exécution manuelle avec dates spécifiques
```bash
# L'utilisateur demande: 2026-01-31 -> 2026-02-01 (week-end)
# Le pipeline ajuste automatiquement: 2026-01-30 -> 2026-01-30 (vendredi)
```

### Historique sur plusieurs années
```bash
# L'utilisateur demande: 2020-01-01 -> 2022-01-01
# Le pipeline traite uniquement les 523 jours de trading (exclut 208 jours de week-end)
```

## Notes Techniques

- Les dates sont ajustées AVANT l'appel à `extract_yahoo_data()`
- La validation `start <= end` est garantie après ajustement
- Compatible avec tous les fuseaux horaires (UTC utilisé dans Airflow)
- Pas d'impact sur les performances (calculs instantanés)
- Logs détaillés pour debugging et traçabilité

## Compatibilité

Cette protection week-end est compatible avec:
- ✓ Yahoo Finance API (intraday 15m + daily)
- ✓ Eurostat API (données macro)
- ✓ Pipeline Wikipedia (non concerné, données statiques)
- ✓ Toutes les couches (Bronze/Silver/Gold)

---

**Date d'implémentation:** 2026-02-02
**Version pipeline:** v4.0
**Status:** ✓ Testé et validé
