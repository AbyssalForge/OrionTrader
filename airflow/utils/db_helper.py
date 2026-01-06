"""
Database helper functions for ETL pipeline
Centralise la gestion des connexions et sessions SQLAlchemy
"""

from models import get_engine, get_session
from utils.vault_helper import get_vault


def get_db_engine():
    """
    Crée un engine SQLAlchemy avec les credentials depuis Vault

    Returns:
        Engine: SQLAlchemy engine configuré
    """
    vault = get_vault()
    db_config = {
        'host': 'postgres',
        'port': 5432,
        'database': vault.get_secret('Database', 'POSTGRES_DB'),
        'user': vault.get_secret('Database', 'POSTGRES_USER'),
        'password': vault.get_secret('Database', 'POSTGRES_PASSWORD')
    }
    connection_string = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    return get_engine(connection_string)


def get_db_session():
    """
    Crée une session SQLAlchemy

    Returns:
        Session: SQLAlchemy session
    """
    engine = get_db_engine()
    return get_session(engine)
