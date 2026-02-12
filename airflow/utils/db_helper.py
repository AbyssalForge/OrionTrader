"""
Database helper functions for ETL pipeline
Centralise la gestion des connexions et sessions SQLAlchemy
"""

import os
from urllib.parse import quote_plus
from models import get_engine, get_session
from clients.vault_helper import get_vault


def get_db_engine():
    """
    Crée un engine SQLAlchemy avec les credentials depuis Vault

    Returns:
        Engine: SQLAlchemy engine configuré
    """
    vault = get_vault()
    db_config = {
        'host': os.getenv('POSTGRES_HOST') or vault.get_secret('Database', 'POSTGRES_HOST'),
        'port': int(os.getenv('POSTGRES_PORT') or vault.get_secret('Database', 'POSTGRES_PORT')),
        'database': vault.get_secret('Database', 'POSTGRES_DB'),
        'user': vault.get_secret('Database', 'POSTGRES_USER'),
        'password': vault.get_secret('Database', 'POSTGRES_PASSWORD')
    }
    connection_string = (
        f"postgresql://{quote_plus(db_config['user'])}:{quote_plus(db_config['password'])}"
        f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    )
    return get_engine(connection_string)


def get_db_session():
    """
    Crée une session SQLAlchemy

    Returns:
        Session: SQLAlchemy session
    """
    engine = get_db_engine()
    return get_session(engine)
