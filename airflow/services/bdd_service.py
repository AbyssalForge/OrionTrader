from models import create_all_tables
from utils.db_helper import get_db_engine

def initialize_database():
    """Crée toutes les tables dans la base de données"""
    print("[INIT] Initialisation base de donnees...")
    engine = get_db_engine()
    create_all_tables(engine)
    print("[INIT] OK: Tables creees")
    return {"status": "success"}
