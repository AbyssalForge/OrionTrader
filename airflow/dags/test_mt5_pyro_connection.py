"""
DAG de test pour valider la connexion Pyro5 avec MetaTrader5.
Ce DAG teste les différentes fonctionnalités du serveur MT5 via Pyro5.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os

# Ajouter le chemin des utils pour les imports
sys.path.insert(0, '/opt/airflow/utils')

from mt5_pyro_client import MT5PyroClient, MT5Timeframe


default_args = {
    'owner': 'oriontrader',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=1),
}


def test_connection():
    """Test la connexion au serveur MT5 Pyro5."""
    print("=" * 80)
    print("TEST 1: Connexion au serveur MT5 Pyro5")
    print("=" * 80)

    try:
        client = MT5PyroClient()
        with client:
            print(f"✓ Connexion établie avec succès")
            ping_response = client.ping()
            print(f"✓ Ping response: {ping_response}")
        return "SUCCESS"
    except Exception as e:
        print(f"✗ Erreur de connexion: {e}")
        raise


def test_version():
    """Test la récupération de la version MT5."""
    print("=" * 80)
    print("TEST 2: Récupération de la version MT5")
    print("=" * 80)

    try:
        client = MT5PyroClient()
        with client:
            version = client.version()
            print(f"✓ Version MT5: {version}")
            return f"Version: {version}"
    except Exception as e:
        print(f"✗ Erreur version: {e}")
        raise


def test_initialize():
    """Test l'initialisation de MT5."""
    print("=" * 80)
    print("TEST 3: Initialisation de MT5")
    print("=" * 80)

    try:
        client = MT5PyroClient()
        with client:
            result = client.initialize()
            if result:
                print(f"✓ MT5 initialisé avec succès")
            else:
                error = client.last_error()
                print(f"✗ Erreur d'initialisation: {error}")
            return "SUCCESS" if result else "FAILED"
    except Exception as e:
        print(f"✗ Erreur initialize: {e}")
        raise


def test_terminal_info():
    """Test la récupération des informations du terminal."""
    print("=" * 80)
    print("TEST 4: Informations du terminal")
    print("=" * 80)

    try:
        client = MT5PyroClient()
        with client:
            client.initialize()
            terminal_info = client.terminal_info()

            if terminal_info:
                print(f"✓ Informations du terminal récupérées:")
                for key, value in list(terminal_info.items())[:10]:  # Afficher les 10 premières clés
                    print(f"  - {key}: {value}")
            else:
                print(f"✗ Aucune information de terminal disponible")

            return "SUCCESS" if terminal_info else "NO_DATA"
    except Exception as e:
        print(f"✗ Erreur terminal_info: {e}")
        raise


def test_account_info():
    """Test la récupération des informations du compte."""
    print("=" * 80)
    print("TEST 5: Informations du compte")
    print("=" * 80)

    try:
        client = MT5PyroClient()
        with client:
            client.initialize()
            account_info = client.account_info()

            if account_info:
                print(f"✓ Informations du compte récupérées:")
                important_keys = ['login', 'balance', 'equity', 'profit', 'margin', 'margin_free']
                for key in important_keys:
                    if key in account_info:
                        print(f"  - {key}: {account_info[key]}")
            else:
                print(f"✗ Aucune information de compte disponible")

            return "SUCCESS" if account_info else "NO_DATA"
    except Exception as e:
        print(f"✗ Erreur account_info: {e}")
        raise


def test_symbols():
    """Test la récupération des symboles disponibles."""
    print("=" * 80)
    print("TEST 6: Symboles disponibles")
    print("=" * 80)

    try:
        client = MT5PyroClient()
        with client:
            client.initialize()

            # Récupérer les symboles Forex
            symbols = client.symbols_get("*EUR*,*USD*")

            if symbols:
                print(f"✓ {len(symbols)} symboles trouvés")
                # Afficher les 5 premiers symboles
                for symbol in symbols[:5]:
                    print(f"  - {symbol.get('name', 'N/A')}: {symbol.get('description', 'N/A')}")
            else:
                print(f"✗ Aucun symbole disponible")

            return f"Found {len(symbols) if symbols else 0} symbols"
    except Exception as e:
        print(f"✗ Erreur symbols_get: {e}")
        raise


def test_symbol_info():
    """Test la récupération des informations d'un symbole spécifique."""
    print("=" * 80)
    print("TEST 7: Informations du symbole EURUSD")
    print("=" * 80)

    try:
        client = MT5PyroClient()
        with client:
            client.initialize()
            symbol_info = client.symbol_info("EURUSD")

            if symbol_info:
                print(f"✓ Informations EURUSD récupérées:")
                important_keys = ['name', 'bid', 'ask', 'spread', 'digits', 'point']
                for key in important_keys:
                    if key in symbol_info:
                        print(f"  - {key}: {symbol_info[key]}")
            else:
                print(f"✗ Symbole EURUSD non disponible")

            return "SUCCESS" if symbol_info else "NO_DATA"
    except Exception as e:
        print(f"✗ Erreur symbol_info: {e}")
        raise


def test_get_rates():
    """Test la récupération des données de marché."""
    print("=" * 80)
    print("TEST 8: Récupération des données EURUSD H1")
    print("=" * 80)

    try:
        client = MT5PyroClient()
        with client:
            client.initialize()

            # Récupérer les 100 dernières barres H1 pour EURUSD
            rates = client.copy_rates_from_pos(
                symbol="EURUSD",
                timeframe=MT5Timeframe.H1,
                start_pos=0,
                count=100
            )

            if rates:
                print(f"✓ {len(rates)} barres récupérées")
                # Afficher les 3 dernières barres
                print("\nDernières barres:")
                for rate in rates[-3:]:
                    time_str = datetime.fromtimestamp(rate['time']).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"  {time_str} - O:{rate['open']:.5f} H:{rate['high']:.5f} L:{rate['low']:.5f} C:{rate['close']:.5f}")
            else:
                print(f"✗ Aucune donnée disponible")

            return f"Retrieved {len(rates) if rates else 0} rates"
    except Exception as e:
        print(f"✗ Erreur copy_rates_from_pos: {e}")
        raise


def test_get_rates_range():
    """Test la récupération des données sur une période."""
    print("=" * 80)
    print("TEST 9: Récupération des données sur période")
    print("=" * 80)

    try:
        client = MT5PyroClient()
        with client:
            client.initialize()

            # Récupérer les données des 7 derniers jours
            date_to = datetime.now()
            date_from = date_to - timedelta(days=7)

            rates = client.copy_rates_range(
                symbol="EURUSD",
                timeframe=MT5Timeframe.H4,
                date_from=date_from,
                date_to=date_to
            )

            if rates:
                print(f"✓ {len(rates)} barres H4 récupérées pour la période {date_from.date()} - {date_to.date()}")
                # Statistiques
                closes = [r['close'] for r in rates]
                print(f"  - Prix min: {min(closes):.5f}")
                print(f"  - Prix max: {max(closes):.5f}")
                print(f"  - Prix moyen: {sum(closes)/len(closes):.5f}")
            else:
                print(f"✗ Aucune donnée disponible")

            return f"Retrieved {len(rates) if rates else 0} rates"
    except Exception as e:
        print(f"✗ Erreur copy_rates_range: {e}")
        raise


def test_positions_and_orders():
    """Test la récupération des positions et ordres."""
    print("=" * 80)
    print("TEST 10: Positions et ordres actifs")
    print("=" * 80)

    try:
        client = MT5PyroClient()
        with client:
            client.initialize()

            # Positions
            positions = client.positions_get()
            if positions:
                print(f"✓ {len(positions)} position(s) ouverte(s)")
                for pos in positions:
                    print(f"  - {pos.get('symbol')} {pos.get('type')} Volume: {pos.get('volume')} Profit: {pos.get('profit')}")
            else:
                print(f"✓ Aucune position ouverte")

            # Ordres
            orders = client.orders_get()
            if orders:
                print(f"✓ {len(orders)} ordre(s) en attente")
                for order in orders:
                    print(f"  - {order.get('symbol')} {order.get('type')} Volume: {order.get('volume_current')}")
            else:
                print(f"✓ Aucun ordre en attente")

            return f"Positions: {len(positions) if positions else 0}, Orders: {len(orders) if orders else 0}"
    except Exception as e:
        print(f"✗ Erreur positions/orders: {e}")
        raise


# Création du DAG
with DAG(
    'test_mt5_pyro_connection',
    default_args=default_args,
    description='Test de la connexion Pyro5 avec MetaTrader5',
    schedule_interval=None,  # Manuel uniquement
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['test', 'mt5', 'pyro5'],
) as dag:

    # Définir les tâches
    task_connection = PythonOperator(
        task_id='test_connection',
        python_callable=test_connection,
    )

    task_version = PythonOperator(
        task_id='test_version',
        python_callable=test_version,
    )

    task_initialize = PythonOperator(
        task_id='test_initialize',
        python_callable=test_initialize,
    )

    task_terminal_info = PythonOperator(
        task_id='test_terminal_info',
        python_callable=test_terminal_info,
    )

    task_account_info = PythonOperator(
        task_id='test_account_info',
        python_callable=test_account_info,
    )

    task_symbols = PythonOperator(
        task_id='test_symbols',
        python_callable=test_symbols,
    )

    task_symbol_info = PythonOperator(
        task_id='test_symbol_info',
        python_callable=test_symbol_info,
    )

    task_get_rates = PythonOperator(
        task_id='test_get_rates',
        python_callable=test_get_rates,
    )

    task_get_rates_range = PythonOperator(
        task_id='test_get_rates_range',
        python_callable=test_get_rates_range,
    )

    task_positions_orders = PythonOperator(
        task_id='test_positions_and_orders',
        python_callable=test_positions_and_orders,
    )

    # Définir l'ordre des tâches
    task_connection >> task_version >> task_initialize >> [
        task_terminal_info,
        task_account_info,
        task_symbols,
        task_symbol_info,
        task_get_rates,
        task_get_rates_range,
        task_positions_orders
    ]
