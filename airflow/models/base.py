"""
Configuration de base pour SQLAlchemy
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


def get_engine(connection_string):
    """
    Crée un engine SQLAlchemy
    """
    return create_engine(connection_string, echo=False)


def get_session(engine):
    """
    Crée une session SQLAlchemy
    """
    Session = sessionmaker(bind=engine)
    return Session()


def create_all_tables(engine):
    """
    Crée toutes les tables dans la base de données
    """
    Base.metadata.create_all(engine)
    print("✅ Toutes les tables ont été créées")


def drop_all_tables(engine):
    """
    Supprime toutes les tables (DANGER!)
    """
    Base.metadata.drop_all(engine)
    print("⚠ Toutes les tables ont été supprimées")
