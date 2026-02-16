"""
Modèles de base de données pour OrionTrader
Pipeline ETL v3 - Architecture 4 tables séparées par source + composites
"""

# Base et fonctions utilitaires
from .base import (
    Base,
    get_engine,
    get_session,
    create_all_tables,
    drop_all_tables,
)

# Architecture 4 Tables Séparées (v3.0)
from .MT5EURUSDM15 import MT5EURUSDM15
from .YahooFinanceDaily import YahooFinanceDaily
from .DocumentsMacro import DocumentsMacro
from .MarketSnapshotM15 import MarketSnapshotM15
from .WikipediaIndices import WikipediaIndices

__all__ = [
    # Base
    'Base',
    'get_engine',
    'get_session',
    'create_all_tables',
    'drop_all_tables',

    # Architecture v3.0 - 4 tables séparées par source + composites
    'MT5EURUSDM15',           # Table 1: MT5 local (M15)
    'YahooFinanceDaily',      # Table 2: Yahoo Finance API (Daily)
    'DocumentsMacro',         # Table 3: Documents économiques (Monthly/Annual)
    'MarketSnapshotM15',      # Table 4: Market snapshot avec features composites
    'WikipediaIndices',       # Table 5: Wikipedia indices (scraping)
]
