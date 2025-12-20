import os
import pandas as pd
import requests
import feedparser
from datetime import datetime

BASE_PATH = "/data/documents"
os.makedirs(BASE_PATH, exist_ok=True)

# Macro Eurozone (ECB)
def get_eurozone_pib():
    url = "https://sdw.ecb.europa.eu/quickviewexport.do?SERIES_KEY=122.1.A.U2.N.0000.4.IN.X.O.N&exportType=csv"
    df = pd.read_csv(url)
    df["TIME_PERIOD"] = pd.to_datetime(df["TIME_PERIOD"], errors="coerce")
    df = df.rename(columns={"OBS_VALUE": "eurozone_pib"})
    df.set_index("TIME_PERIOD", inplace=True)
    path = os.path.join(BASE_PATH, "eurozone_pib.parquet")
    df.to_parquet(path)
    return path

def get_eurozone_cpi():
    url = "https://sdw.ecb.europa.eu/quickviewexport.do?SERIES_KEY=ICP.M.U2.N.000000.4.INX&exportType=csv"
    df = pd.read_csv(url)
    df["TIME_PERIOD"] = pd.to_datetime(df["TIME_PERIOD"], errors="coerce")
    df = df.rename(columns={"OBS_VALUE": "eurozone_cpi"})
    df.set_index("TIME_PERIOD", inplace=True)
    path = os.path.join(BASE_PATH, "eurozone_cpi.parquet")
    df.to_parquet(path)
    return path

# Calendrier économique (RSS)
def get_economic_events():
    rss_url = "https://www.forexfactory.com/ffcal_week_this.xml"
    feed = feedparser.parse(rss_url)
    
    events = []
    for entry in feed.entries:
        events.append({
            "time": pd.to_datetime(entry.published),
            "title": entry.title,
            "impact": entry.tags[0]["term"] if entry.tags else None
        })
    
    df = pd.DataFrame(events)
    path = os.path.join(BASE_PATH, "economic_events.parquet")
    df.to_parquet(path)
    return path

# Fonction globale pour la task Airflow
def extract_documents():
    return {
        "pib": get_eurozone_pib(),
        "cpi": get_eurozone_cpi(),
        "events": get_economic_events()
    }
