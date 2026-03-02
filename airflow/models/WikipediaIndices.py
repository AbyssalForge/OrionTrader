"""
TABLE 5 - Source Wikipedia (Scraping)
Référentiel des indices boursiers
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Index
from datetime import datetime
from .base import Base


class WikipediaIndices(Base):
    """
    Table 5/5 - Wikipedia Indices

    Source: Wikipedia (web scraping)
    Fréquence: Hebdomadaire/Mensuel (données quasi-statiques)
    Type: Référentiel marché (composants d'indices)

    Indices scrapés:
    - CAC 40 (France)
    - S&P 500 (USA)
    - NASDAQ 100 (USA)
    - Dow Jones Industrial Average (USA)

    Colonnes: 15
    Volume: ~700 entreprises uniques
    Taille: ~100 KB

    Utilisation ML:
    - Mapping ticker → secteur
    - Classification par secteur
    - Analyse fondamentale par industrie
    - Filtrage par pays/région
    """
    __tablename__ = 'wikipedia_indices'

    # Clé primaire composite (ticker unique)
    ticker = Column(String(20), primary_key=True)

    # Informations entreprise
    company_name = Column(String(200), nullable=False)
    sector = Column(String(100))
    country = Column(String(100))
    region = Column(String(100))

    # Métadonnées indices
    index_name = Column(String(100))        # Premier indice (pour dédupliqués)
    index_key = Column(String(50))          # Clé de l'indice (CAC40, SP500, etc.)
    num_indices = Column(Integer)           # Nombre d'indices contenant ce ticker
    is_multi_index = Column(Boolean)        # Présent dans plusieurs indices

    # Champs dérivés
    ticker_company = Column(String(250))    # "AAPL - Apple Inc."

    # Timestamps
    scraped_at = Column(DateTime(timezone=True))      # Quand scrapé depuis Wikipedia
    transformed_at = Column(DateTime(timezone=True))  # Quand transformé (Silver)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    pipeline_run_id = Column(String(100))

    __table_args__ = (
        Index('idx_wiki_ticker', 'ticker'),
        Index('idx_wiki_sector', 'sector'),
        Index('idx_wiki_country', 'country'),
        Index('idx_wiki_index', 'index_key'),
        Index('idx_wiki_pipeline', 'pipeline_run_id'),
    )
