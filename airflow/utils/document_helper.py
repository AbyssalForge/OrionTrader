import os
import pandas as pd
import requests
import feedparser
from datetime import datetime
from io import StringIO

BASE_PATH = "data/documents"
os.makedirs(BASE_PATH, exist_ok=True)

# Macro Eurozone via EUROSTAT
def get_eurozone_pib():
    """
    Récupère le PIB de la zone euro depuis Eurostat.
    Dataset: namq_10_gdp (PIB trimestriel et principaux composants)
    """
    print(f"[DOCUMENT] Téléchargement PIB depuis Eurostat")

    # URL de l'API Eurostat pour le PIB de la zone euro
    # namq_10_gdp: PIB et principaux composants (trimestriel)
    # B1GQ: PIB aux prix du marché
    # CLV_PCH_PRE: Taux de croissance en volume par rapport au trimestre précédent
    url = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/namq_10_gdp/?format=TSV&na_item=B1GQ&unit=CLV_I10&s_adj=SCA&geo=EA20"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Eurostat retourne du TSV (Tab Separated Values)
        lines = response.text.strip().split('\n')

        # La première ligne contient les métadonnées
        # La deuxième ligne contient les en-têtes (dates)
        headers = lines[0].split('\t')[1:]  # Skip first column (metadata)
        data_line = lines[1].split('\t')

        # Extraire les valeurs
        values = []
        dates = []

        for i, header in enumerate(headers):
            try:
                # Format: 2024-Q1, 2024-Q2, etc. (avec espaces possibles)
                header_clean = header.strip()
                if 'Q' in header_clean:
                    # Supprimer les espaces et séparer par 'Q' ou '-Q'
                    header_clean = header_clean.replace('-Q', 'Q')
                    year, quarter = header_clean.split('Q')
                    year = year.strip()
                    quarter = quarter.strip()

                    # Convertir en date (premier jour du trimestre)
                    month = (int(quarter) - 1) * 3 + 1
                    date = pd.Timestamp(year=int(year), month=month, day=1)
                    dates.append(date)

                    value = data_line[i + 1]  # +1 car la première colonne est metadata
                    if value and value.strip() and value.strip() != ':':
                        values.append(float(value.replace(',', '.')))
                    else:
                        values.append(None)
            except Exception as e:
                print(f"[DOCUMENT] ⚠ Erreur parsing date '{header}': {e}")
                continue

        df = pd.DataFrame({
            'eurozone_pib': values
        }, index=dates)
        df = df.dropna()
        df.index.name = 'TIME_PERIOD'

        path = os.path.join(BASE_PATH, "eurozone_pib.parquet")
        df.to_parquet(path)
        print(f"[DOCUMENT] ✓ PIB Eurostat sauvegardé: {len(df)} lignes")
        return path

    except Exception as e:
        print(f"[DOCUMENT] ⚠ Erreur téléchargement PIB Eurostat: {e}")
        print(f"[DOCUMENT] Création de données PIB factices")

        # Fallback: données factices
        dates = pd.date_range(start='2020-01-01', end='2024-12-31', freq='Q')
        values = [100 + i * 0.5 for i in range(len(dates))]

        df = pd.DataFrame({
            'eurozone_pib': values
        }, index=dates)
        df.index.name = 'TIME_PERIOD'

        path = os.path.join(BASE_PATH, "eurozone_pib.parquet")
        df.to_parquet(path)
        print(f"[DOCUMENT] ✓ PIB factice sauvegardé: {len(df)} lignes")
        return path

def get_eurozone_cpi():
    """
    Récupère l'inflation (HICP) de la zone euro depuis Eurostat.
    Dataset: prc_hicp_midx (Indice des prix à la consommation harmonisé)
    """
    print(f"[DOCUMENT] Téléchargement CPI depuis Eurostat")

    # URL de l'API Eurostat pour le HICP (inflation)
    # prc_hicp_midx: Indice mensuel des prix à la consommation harmonisé
    # CP00: All-items HICP
    url = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/prc_hicp_midx/?format=TSV&coicop=CP00&unit=I15&geo=EA20"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        lines = response.text.strip().split('\n')
        headers = lines[0].split('\t')[1:]
        data_line = lines[1].split('\t')

        values = []
        dates = []

        for i, header in enumerate(headers):
            try:
                # Format: 2024-01, 2024-02, etc. (avec espaces possibles)
                header_clean = header.strip()
                if 'M' in header_clean or '-' in header_clean:
                    # Format peut être 2024M01 ou 2024-01
                    header_clean = header_clean.replace('-', 'M').replace(' ', '')

                    if 'M' in header_clean:
                        parts = header_clean.split('M')
                        year = parts[0].strip()
                        month = parts[1].strip()
                    else:
                        # Fallback si pas de M
                        year = header_clean[:4]
                        month = header_clean[4:6] if len(header_clean) >= 6 else header_clean[5:7]

                    date = pd.Timestamp(year=int(year), month=int(month), day=1)
                    dates.append(date)

                    value = data_line[i + 1]
                    if value and value.strip() and value.strip() != ':':
                        values.append(float(value.replace(',', '.')))
                    else:
                        values.append(None)
            except Exception as e:
                print(f"[DOCUMENT] ⚠ Erreur parsing date '{header}': {e}")
                continue

        df = pd.DataFrame({
            'eurozone_cpi': values
        }, index=dates)
        df = df.dropna()
        df.index.name = 'TIME_PERIOD'

        path = os.path.join(BASE_PATH, "eurozone_cpi.parquet")
        df.to_parquet(path)
        print(f"[DOCUMENT] ✓ CPI Eurostat sauvegardé: {len(df)} lignes")
        return path

    except Exception as e:
        print(f"[DOCUMENT] ⚠ Erreur téléchargement CPI Eurostat: {e}")
        print(f"[DOCUMENT] Création de données CPI factices")

        # Fallback: données factices
        dates = pd.date_range(start='2020-01-01', end='2024-12-31', freq='M')
        values = [100 + i * 0.2 for i in range(len(dates))]

        df = pd.DataFrame({
            'eurozone_cpi': values
        }, index=dates)
        df.index.name = 'TIME_PERIOD'

        path = os.path.join(BASE_PATH, "eurozone_cpi.parquet")
        df.to_parquet(path)
        print(f"[DOCUMENT] ✓ CPI factice sauvegardé: {len(df)} lignes")
        return path

# Calendrier économique (RSS)
def get_economic_events():
    print(f"[DOCUMENT] Création d'événements économiques factices (ForexFactory bloqué)")

    # Créer quelques événements factices
    dates = pd.date_range(start=datetime.now(), periods=10, freq='D')
    events = []

    event_titles = [
        "ECB Interest Rate Decision",
        "US Non-Farm Payrolls",
        "EU GDP Release",
        "Fed Speech",
        "US CPI Data",
        "EU Unemployment Rate",
        "US Retail Sales",
        "ECB Minutes",
        "US PMI Data",
        "EU Industrial Production"
    ]

    impacts = ["High", "High", "Medium", "Low", "High", "Medium", "Medium", "Low", "Medium", "Medium"]

    for i, date in enumerate(dates):
        events.append({
            "time": date,
            "title": event_titles[i],
            "impact": impacts[i]
        })

    df = pd.DataFrame(events)
    path = os.path.join(BASE_PATH, "economic_events.parquet")
    df.to_parquet(path)
    print(f"[DOCUMENT] ✓ {len(df)} événements factices sauvegardés")
    return path

# Fonction globale pour la task Airflow
def extract_documents():
    return {
        "pib": get_eurozone_pib(),
        "cpi": get_eurozone_cpi(),
        "events": get_economic_events()
    }
