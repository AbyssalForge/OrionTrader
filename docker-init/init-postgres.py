"""
Initialize PostgreSQL databases and users for OrionTrader
Replaces init-postgres.sh to avoid CRLF line ending issues on Windows
"""

import os
import sys
import time
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

POSTGRES_HOST = os.environ.get('POSTGRES_HOST', 'postgres')
POSTGRES_PORT = int(os.environ.get('POSTGRES_PORT', 5432))
POSTGRES_USER = os.environ['POSTGRES_USER']
POSTGRES_PASSWORD = os.environ['POSTGRES_PASSWORD']
POSTGRES_DB = os.environ.get('POSTGRES_DB', 'trading_data')

AIRFLOW_DB = os.environ.get('AIRFLOW_DB_NAME', 'airflow')
AIRFLOW_USER = os.environ.get('AIRFLOW_DB_USER', 'airflow')
AIRFLOW_PASSWORD = os.environ.get('AIRFLOW_DB_PASSWORD', 'airflow')

MLFLOW_DB = os.environ.get('MLFLOW_DB_NAME', 'mlflow')
MLFLOW_USER = os.environ.get('MLFLOW_DB_USER', 'mlflow')
MLFLOW_PASSWORD = os.environ.get('MLFLOW_DB_PASSWORD', 'mlflow')

FASTAPI_DB = os.environ.get('FASTAPI_DB_NAME', 'fastapi')
FASTAPI_USER = os.environ.get('FASTAPI_DB_USER', 'fastapi')
FASTAPI_PASSWORD = os.environ.get('FASTAPI_DB_PASSWORD', 'fastapi')

STREAMLIT_USER = os.environ.get('STREAMLIT_DB_USER', 'streamlit')
STREAMLIT_PASSWORD = os.environ.get('STREAMLIT_DB_PASSWORD', 'streamlit')


def connect(dbname=None):
    return psycopg2.connect(
        host=POSTGRES_HOST, port=POSTGRES_PORT,
        user=POSTGRES_USER, password=POSTGRES_PASSWORD,
        dbname=dbname or POSTGRES_DB
    )


def wait_for_postgres():
    print("=" * 60)
    print("Waiting for PostgreSQL to be ready...")
    print("=" * 60)
    for attempt in range(1, 61):
        try:
            connect().close()
            print("PostgreSQL is up - executing database initialization\n")
            return
        except psycopg2.OperationalError:
            print(f"PostgreSQL unavailable - attempt {attempt}/60")
            time.sleep(1)
    print("ERROR: PostgreSQL did not become ready in time")
    sys.exit(1)


def create_or_update_user(cur, username, password):
    cur.execute("SELECT 1 FROM pg_user WHERE usename = %s", (username,))
    if cur.fetchone():
        cur.execute(f"ALTER USER {username} WITH PASSWORD %s", (password,))
        print(f"  [OK] User {username} password updated")
    else:
        cur.execute(f"CREATE USER {username} WITH PASSWORD %s", (password,))
        print(f"  [OK] User {username} created")


def create_db_if_not_exists(conn, dbname, owner):
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
    if not cur.fetchone():
        cur.execute(f'CREATE DATABASE "{dbname}" OWNER {owner}')
        print(f"  [OK] Database {dbname} created")
    else:
        print(f"  [SKIP] Database {dbname} already exists")
    cur.close()


def grant_all(cur, schema_user):
    cur.execute(f"GRANT ALL ON SCHEMA public TO {schema_user}")
    cur.execute(f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {schema_user}")
    cur.execute(f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {schema_user}")
    cur.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {schema_user}")
    cur.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO {schema_user}")


def grant_read(cur, schema_user, dbname):
    cur.execute(f"GRANT CONNECT ON DATABASE {dbname} TO {schema_user}")
    cur.execute(f"GRANT USAGE ON SCHEMA public TO {schema_user}")
    cur.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {schema_user}")
    cur.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {schema_user}")


def main():
    wait_for_postgres()

    print("[1/4] Creating users...")
    conn = connect()
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    create_or_update_user(cur, AIRFLOW_USER, AIRFLOW_PASSWORD)
    create_or_update_user(cur, MLFLOW_USER, MLFLOW_PASSWORD)
    create_or_update_user(cur, FASTAPI_USER, FASTAPI_PASSWORD)
    create_or_update_user(cur, STREAMLIT_USER, STREAMLIT_PASSWORD)
    cur.close()
    conn.close()

    print("\n[2/4] Creating databases...")
    conn = connect()
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    create_db_if_not_exists(conn, AIRFLOW_DB, AIRFLOW_USER)
    create_db_if_not_exists(conn, MLFLOW_DB, MLFLOW_USER)
    create_db_if_not_exists(conn, FASTAPI_DB, FASTAPI_USER)
    conn.close()

    print(f"\n[3/4] Setting permissions on {POSTGRES_DB}...")
    conn = connect()
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    grant_all(cur, AIRFLOW_USER)
    grant_read(cur, FASTAPI_USER, POSTGRES_DB)
    grant_read(cur, STREAMLIT_USER, POSTGRES_DB)
    cur.close()
    conn.close()
    print(f"  [OK] Airflow: read/write | FastAPI: read | Streamlit: read")

    print("\n[4/4] Setting permissions on service databases...")
    for dbname, user in [(AIRFLOW_DB, AIRFLOW_USER), (MLFLOW_DB, MLFLOW_USER), (FASTAPI_DB, FASTAPI_USER)]:
        conn = connect(dbname)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        grant_all(cur, user)
        cur.close()
        conn.close()
        print(f"  [OK] {dbname}: {user} has all privileges")

    print("\n" + "=" * 60)
    print("Database initialization completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
