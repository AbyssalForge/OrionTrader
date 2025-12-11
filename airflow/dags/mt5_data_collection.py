"""
DAG Airflow pour collecter les données de trading depuis MetaTrader5.
Démontre l'utilisation du client MT5 via RPyC.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import os
import sys

# Ajouter le chemin des utils au PYTHONPATH
sys.path.insert(0, '/opt/airflow/utils')

from mt5_client import MT5Client, MT5Timeframe


def test_mt5_connection(**context):
    """Teste la connexion au serveur MT5."""
    print("Testing MT5 connection...")

    with MT5Client() as mt5:
        # Récupérer la version
        version = mt5.version()
        print(f"MT5 Version: {version}")

        # Récupérer les infos du terminal
        terminal_info = mt5.terminal_info()
        if terminal_info:
            print(f"Terminal info: {terminal_info}")

        print("Connection test successful!")

    return {"status": "success", "version": version}


def get_account_info(**context):
    """Récupère les informations du compte de trading."""
    print("Fetching account information...")

    with MT5Client() as mt5:
        # Initialiser avec les identifiants (optionnel si déjà connecté)
        mt5_login = os.getenv('MT5_LOGIN')
        mt5_password = os.getenv('MT5_PASSWORD')
        mt5_server = os.getenv('MT5_SERVER')

        if mt5_login and mt5_password and mt5_server:
            mt5.initialize(int(mt5_login), mt5_password, mt5_server)

        # Récupérer les infos du compte
        account_info = mt5.account_info()
        if account_info:
            print(f"Account Info:")
            print(f"  Login: {account_info.get('login')}")
            print(f"  Balance: {account_info.get('balance')}")
            print(f"  Equity: {account_info.get('equity')}")
            print(f"  Margin: {account_info.get('margin')}")
            print(f"  Free Margin: {account_info.get('margin_free')}")
            print(f"  Profit: {account_info.get('profit')}")

            # Pousser les données vers XCom pour les autres tâches
            context['ti'].xcom_push(key='account_info', value=account_info)

            return account_info
        else:
            print("Failed to retrieve account info")
            return None


def get_symbols_list(**context):
    """Récupère la liste des symboles disponibles."""
    print("Fetching symbols list...")

    with MT5Client() as mt5:
        # Récupérer tous les symboles Forex
        symbols = mt5.symbols_get("*EUR*,*USD*,*GBP*")

        if symbols:
            print(f"Found {len(symbols)} symbols")
            symbols_names = [s['name'] for s in symbols[:10]]  # Limiter à 10 pour l'exemple
            print(f"First 10 symbols: {symbols_names}")

            context['ti'].xcom_push(key='symbols', value=symbols_names)
            return symbols_names
        else:
            print("Failed to retrieve symbols")
            return []


def fetch_market_data(**context):
    """Récupère les données de marché pour EURUSD."""
    print("Fetching market data for EURUSD...")

    with MT5Client() as mt5:
        symbol = "EURUSD"

        # Récupérer le dernier tick
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            print(f"Latest tick for {symbol}:")
            print(f"  Bid: {tick.get('bid')}")
            print(f"  Ask: {tick.get('ask')}")
            print(f"  Last: {tick.get('last')}")
            print(f"  Volume: {tick.get('volume')}")

        # Récupérer les 100 dernières barres H1
        rates = mt5.copy_rates_from_pos(
            symbol=symbol,
            timeframe=MT5Timeframe.H1,
            start_pos=0,
            count=100
        )

        if rates:
            print(f"Retrieved {len(rates)} bars for {symbol} H1")
            print(f"Latest bar: {rates[-1] if rates else 'None'}")

            # Sauvegarder dans XCom
            context['ti'].xcom_push(key='market_data', value={
                'symbol': symbol,
                'tick': tick,
                'bars_count': len(rates),
                'latest_bar': rates[-1] if rates else None
            })

            return rates
        else:
            print("Failed to retrieve market data")
            return []


def get_positions(**context):
    """Récupère les positions ouvertes."""
    print("Fetching open positions...")

    with MT5Client() as mt5:
        positions = mt5.positions_get()

        if positions:
            print(f"Found {len(positions)} open positions")
            for pos in positions:
                print(f"  Position #{pos.get('ticket')}: {pos.get('symbol')} "
                      f"{pos.get('type')} Volume: {pos.get('volume')} "
                      f"Profit: {pos.get('profit')}")

            context['ti'].xcom_push(key='positions', value=positions)
            return positions
        else:
            print("No open positions")
            return []


def save_to_database(**context):
    """
    Sauvegarde les données collectées dans PostgreSQL.
    Cette fonction peut être étendue pour sauvegarder dans votre base de données.
    """
    print("Saving data to database...")

    # Récupérer les données depuis XCom
    ti = context['ti']
    account_info = ti.xcom_pull(key='account_info', task_ids='get_account_info')
    market_data = ti.xcom_pull(key='market_data', task_ids='fetch_market_data')
    positions = ti.xcom_pull(key='positions', task_ids='get_positions')

    print(f"Account Info: {account_info}")
    print(f"Market Data: {market_data}")
    print(f"Positions: {len(positions) if positions else 0}")

    # TODO: Implémenter la sauvegarde dans PostgreSQL
    # Exemple:
    # import psycopg2
    # conn = psycopg2.connect(...)
    # cur = conn.cursor()
    # cur.execute("INSERT INTO market_data ...")

    print("Data saved successfully!")
    return {"status": "success"}


# Définition du DAG
default_args = {
    'owner': 'oriontrader',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'mt5_data_collection',
    default_args=default_args,
    description='Collecte les données de trading depuis MetaTrader5',
    schedule='*/15 * * * *',  # Toutes les 15 minutes
    catchup=False,
    tags=['metatrader5', 'trading', 'data-collection'],
) as dag:

    # Tâche 1: Tester la connexion
    test_connection = PythonOperator(
        task_id='test_mt5_connection',
        python_callable=test_mt5_connection,
        provide_context=True,
    )

    # Tâche 2: Récupérer les infos du compte
    get_account = PythonOperator(
        task_id='get_account_info',
        python_callable=get_account_info,
        provide_context=True,
    )

    # Tâche 3: Récupérer la liste des symboles
    get_symbols = PythonOperator(
        task_id='get_symbols_list',
        python_callable=get_symbols_list,
        provide_context=True,
    )

    # Tâche 4: Récupérer les données de marché
    fetch_data = PythonOperator(
        task_id='fetch_market_data',
        python_callable=fetch_market_data,
        provide_context=True,
    )

    # Tâche 5: Récupérer les positions
    get_open_positions = PythonOperator(
        task_id='get_positions',
        python_callable=get_positions,
        provide_context=True,
    )

    # Tâche 6: Sauvegarder dans la base de données
    save_data = PythonOperator(
        task_id='save_to_database',
        python_callable=save_to_database,
        provide_context=True,
    )

    # Définir les dépendances
    test_connection >> [get_account, get_symbols, fetch_data, get_open_positions]
    [get_account, get_symbols, fetch_data, get_open_positions] >> save_data
