"""
OrionTrader API v1.0 - Point d'entrée principal
FastAPI application pour accès aux données de trading EUR/USD

Architecture modulaire:
- app/core: Database, Vault, Dependencies
- app/schemas: Pydantic models
- app/routes: Endpoints API
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime

from app.config import settings
from app.core import get_db
from app.core.database import test_connection, get_table_counts
from app.routes import market, data, signals


# ============================================================================
# APPLICATION SETUP
# ============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    description="""🚀 **API de trading pour EUR/USD** avec données multi-sources et signaux ML

## Architecture des données

- **MT5 (M15)**: Prix haute fréquence + microstructure (15 minutes)
- **Yahoo Finance (Daily)**: Indicateurs macro-financiers quotidiens
- **Documents Macro**: Données économiques (PIB, inflation, taux directeurs)
- **Market Snapshot**: Features composites + régimes de marché + signaux

## 📋 Endpoints disponibles

### 📊 Market Data (7 endpoints)
- `GET /market/latest` - Dernier snapshot de marché disponible
- `GET /market/ohlcv/m15` - Données OHLCV M15 pour charting
- `GET /market/ohlcv/latest` - Dernier prix OHLCV disponible
- `GET /market/snapshot` - Historique snapshots avec filtres avancés
- `GET /market/regimes` - Distribution des régimes de marché
- `GET /market/stats` - Statistiques de marché agrégées
- `GET /health` - Health check et état des tables

### 🎯 Data & Features (6 endpoints)
- `GET /data/features/mt5` - Features microstructure MT5 (volatilité, momentum, chandeliers)
- `GET /data/features/yahoo` - Features macro Yahoo Finance (DXY, VIX, yields, sentiment)
- `GET /data/features/macro` - Features économiques (PIB, inflation, taux, chômage)
- `GET /data/features/latest` - Dernières features de toutes les sources
- `GET /data/training` - Dataset complet avec JOINs pour ML
- `GET /data/stats` - Statistiques sur les données disponibles

### 🚨 Trading Signals (5 endpoints)
- `GET /signals/high-confidence` - Signaux haute confiance avec filtres
- `GET /signals/best` - Top N meilleurs signaux (score + cohérence)
- `GET /signals/strong-trend` - Signaux avec forte tendance (bullish/bearish)
- `GET /signals/event-window` - Signaux pendant fenêtres d'événements macro
- `GET /signals/stats` - Statistiques et distribution des signaux

## 💡 Use cases

- **📈 Trading automatique**: Utiliser `/signals/high-confidence` pour décisions automatiques
- **📊 Backtesting**: Dataset complet via `/data/training` avec toutes les features
- **🤖 Machine Learning**: Features séparées via `/data/features/*` pour entraînement
- **📉 Analyse technique**: OHLCV haute fréquence via `/market/ohlcv/m15`
- **🌍 Analyse macro**: Données économiques via `/data/features/macro`
- **🎯 Monitoring**: Health check via `/health` et statistiques via `*/stats`

## 🔑 Paramètres principaux

- **Pagination**: `limit` et `offset` sur la plupart des endpoints
- **Filtrage temporel**: `start_date` et `end_date` au format ISO
- **Filtres signaux**: `min_confidence`, `regime`, `volatility_regime`
- **Filtres tendance**: `direction` (bullish/bearish), `min_trend_strength`
""",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ============================================================================
# CORS MIDDLEWARE
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# INCLUDE ROUTERS
# ============================================================================

app.include_router(market.router, prefix="/market", tags=["Market"])
app.include_router(data.router, prefix="/data", tags=["Data & Features"])
app.include_router(signals.router, prefix="/signals", tags=["Trading Signals"])


# ============================================================================
# ROOT & HEALTH ENDPOINTS
# ============================================================================

@app.get("/", tags=["Root"])
def read_root():
    """
    🏠 Page d'accueil de l'API

    Retourne les informations de base et les liens vers la documentation.
    """
    return {
        "message": f"{settings.APP_NAME} v{settings.APP_VERSION}",
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "documentation": "/docs",
        "alternative_docs": "/redoc",
    }


@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """
    ❤️ Health check complet

    Vérifie:
    - Status de l'API
    - Connexion à la base de données
    - Nombre de lignes dans chaque table
    """
    # Test connexion
    db_connected = test_connection()

    # Compter les lignes si connecté
    tables = {}
    if db_connected:
        try:
            tables = get_table_counts()
        except Exception as e:
            tables = {"error": str(e)}

    return {
        "status": "ok" if db_connected else "error",
        "database": "connected" if db_connected else "disconnected",
        "timestamp": datetime.now(),
        "tables": tables
    }


# ============================================================================
# STARTUP & SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Événement au démarrage de l'application"""
    print("=" * 70)
    print(f"[INFO] {settings.APP_NAME} v{settings.APP_VERSION} - Starting...")
    print(f"[INFO] Environment: {settings.ENVIRONMENT}")
    print("=" * 70)

    # Test connexion DB
    if test_connection():
        print("[OK] Database connection: OK")
    else:
        print("[ERROR] Database connection: FAILED")
        print("[WARNING] API will start but endpoints will fail")

    print("=" * 70)
    print("[INFO] Documentation available at: http://localhost:8000/docs")
    print("=" * 70)


@app.on_event("shutdown")
async def shutdown_event():
    """Événement à l'arrêt de l'application"""
    print("=" * 70)
    print(f"[INFO] {settings.APP_NAME} - Shutting down...")
    print("=" * 70)


# ============================================================================
# RUN (for development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
