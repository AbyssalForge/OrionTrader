"""
TABLE 3 - Source Documents Économiques
Données macro fondamentales (PIB, CPI, Events)
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Index
from datetime import datetime
from .base import Base


class DocumentsMacro(Base):
    """
    Table 3/3 - Documents Économiques

    Sources: OECD, World Bank, ECB, Investing.com
    Fréquence: Variable (Annual, Monthly, Ponctuel)
    Type: Fondamentaux macro-économiques

    Colonnes: 9 (PIB, CPI, Events)
    Volume: ~50 lignes pour 2 ans
    Taille: ~10 KB

    Données:
    - PIB Eurozone (Annual): Croissance économique
    - CPI Eurozone (Monthly): Inflation
    - Events Économiques (Ponctuel): Publications importantes

    Utilisation ML:
    - Contexte macro fondamental
    - Régime économique (croissance, inflation)
    - Impact événements macro

    Note Architecture:
    Cette table garde la fréquence NATIVE des données (monthly/annual).
    Pas de resample ou duplication. La jointure temporelle se fait
    lors de l'utilisation ML avec merge_asof (backward fill).

    Avantages:
    - Pas de duplication (PIB pas répété 70k fois)
    - Respect de la fréquence native
    - Facilite l'ajout de nouvelles sources macro
    - Architecture plus propre et maintenable
    """
    __tablename__ = 'documents_macro'

    time = Column(DateTime(timezone=True), primary_key=True)

    # Metadata pour identifier le type de donnée
    data_type = Column(String(50))      # 'pib', 'cpi', 'event'
    frequency = Column(String(20))      # 'annual', 'monthly', 'punctual'

    # ===== PIB Eurozone (3 colonnes) =====
    eurozone_pib = Column(Float)        # Croissance PIB % (annual)
    pib_change = Column(Float)          # Variation vs année précédente
    pib_growth = Column(Float)          # Accélération/décélération

    # ===== CPI Eurozone (3 colonnes) =====
    eurozone_cpi = Column(Float)        # Inflation CPI % (monthly)
    cpi_change = Column(Float)          # Variation vs mois précédent
    inflation_pressure = Column(Integer) # Binaire: CPI > 2% (cible BCE)

    # ===== Events Économiques (3 colonnes) =====
    event_title = Column(String(200))   # Nom événement (ex: "BCE Rate Decision")
    event_impact = Column(String(50))   # Impact attendu: 'high', 'medium', 'low'
    event_impact_score = Column(Float)  # Score numérique impact (0-1)

    # ===== Metadata (2 colonnes) =====
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    pipeline_run_id = Column(String(100))

    __table_args__ = (
        Index('idx_documents_time', 'time'),
        Index('idx_documents_type', 'data_type'),
        Index('idx_documents_frequency', 'frequency'),
        Index('idx_documents_pipeline', 'pipeline_run_id'),
    )
