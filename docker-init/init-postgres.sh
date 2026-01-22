#!/bin/bash
set -e

# ============================================================================
# VARIABLES DE CONFIGURATION
# ============================================================================

TRADING_DB_NAME="${POSTGRES_DB:-trading_data}"

AIRFLOW_DB_NAME="${AIRFLOW_DB_NAME:-airflow}"
AIRFLOW_DB_USER="${AIRFLOW_DB_USER:-airflow}"
AIRFLOW_DB_PASSWORD="${AIRFLOW_DB_PASSWORD:-airflow}"

MLFLOW_DB_NAME="${MLFLOW_DB_NAME:-mlflow}"
MLFLOW_DB_USER="${MLFLOW_DB_USER:-mlflow}"
MLFLOW_DB_PASSWORD="${MLFLOW_DB_PASSWORD:-mlflow}"

FASTAPI_DB_NAME="${FASTAPI_DB_NAME:-fastapi}"
FASTAPI_DB_USER="${FASTAPI_DB_USER:-fastapi}"
FASTAPI_DB_PASSWORD="${FASTAPI_DB_PASSWORD:-fastapi}"

STREAMLIT_DB_USER="${STREAMLIT_DB_USER:-streamlit}"
STREAMLIT_DB_PASSWORD="${STREAMLIT_DB_PASSWORD:-streamlit}"

echo "============================================================================"
echo "Waiting for PostgreSQL to be ready..."
echo "============================================================================"

max_attempts=60
attempt=0

until PGPASSWORD=$POSTGRES_PASSWORD psql -h postgres -U $POSTGRES_USER -d $TRADING_DB_NAME -c '\q' 2>/dev/null; do
  attempt=$((attempt + 1))
  if [ $attempt -ge $max_attempts ]; then
    echo "ERROR: PostgreSQL did not become ready in time"
    exit 1
  fi
  echo "PostgreSQL is unavailable - attempt $attempt/$max_attempts"
  sleep 1
done

echo "PostgreSQL is up - executing database initialization"
echo ""

# ============================================================================
# CREATION DES UTILISATEURS
# ============================================================================

echo "[1/4] Creation des utilisateurs..."

PGPASSWORD=$POSTGRES_PASSWORD psql -h postgres -U $POSTGRES_USER -d $TRADING_DB_NAME <<-EOSQL
    DO \$\$
    BEGIN
        -- Utilisateur Airflow
        IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '${AIRFLOW_DB_USER}') THEN
            CREATE USER ${AIRFLOW_DB_USER} WITH PASSWORD '${AIRFLOW_DB_PASSWORD}';
            RAISE NOTICE '[OK] User ${AIRFLOW_DB_USER} created';
        ELSE
            RAISE NOTICE '[SKIP] User ${AIRFLOW_DB_USER} already exists';
        END IF;

        -- Utilisateur MLflow
        IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '${MLFLOW_DB_USER}') THEN
            CREATE USER ${MLFLOW_DB_USER} WITH PASSWORD '${MLFLOW_DB_PASSWORD}';
            RAISE NOTICE '[OK] User ${MLFLOW_DB_USER} created';
        ELSE
            RAISE NOTICE '[SKIP] User ${MLFLOW_DB_USER} already exists';
        END IF;

        -- Utilisateur FastAPI
        IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '${FASTAPI_DB_USER}') THEN
            CREATE USER ${FASTAPI_DB_USER} WITH PASSWORD '${FASTAPI_DB_PASSWORD}';
            RAISE NOTICE '[OK] User ${FASTAPI_DB_USER} created';
        ELSE
            RAISE NOTICE '[SKIP] User ${FASTAPI_DB_USER} already exists';
        END IF;

        -- Utilisateur Streamlit (lecture seule)
        IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '${STREAMLIT_DB_USER}') THEN
            CREATE USER ${STREAMLIT_DB_USER} WITH PASSWORD '${STREAMLIT_DB_PASSWORD}';
            RAISE NOTICE '[OK] User ${STREAMLIT_DB_USER} created';
        ELSE
            RAISE NOTICE '[SKIP] User ${STREAMLIT_DB_USER} already exists';
        END IF;
    END
    \$\$;
EOSQL

# ============================================================================
# CREATION DES BASES DE DONNEES
# ============================================================================

echo ""
echo "[2/4] Creation des bases de donnees..."

PGPASSWORD=$POSTGRES_PASSWORD psql -h postgres -U $POSTGRES_USER -d $TRADING_DB_NAME <<-EOSQL
    -- Base Airflow
    SELECT 'CREATE DATABASE ${AIRFLOW_DB_NAME} OWNER ${AIRFLOW_DB_USER}'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${AIRFLOW_DB_NAME}')\gexec

    -- Base MLflow
    SELECT 'CREATE DATABASE ${MLFLOW_DB_NAME} OWNER ${MLFLOW_DB_USER}'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${MLFLOW_DB_NAME}')\gexec

    -- Base FastAPI (authentification)
    SELECT 'CREATE DATABASE ${FASTAPI_DB_NAME} OWNER ${FASTAPI_DB_USER}'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${FASTAPI_DB_NAME}')\gexec
EOSQL

# ============================================================================
# PERMISSIONS SUR LA BASE TRADING_DATA
# ============================================================================

echo ""
echo "[3/4] Configuration des permissions sur ${TRADING_DB_NAME}..."

PGPASSWORD=$POSTGRES_PASSWORD psql -h postgres -U $POSTGRES_USER -d $TRADING_DB_NAME <<-EOSQL
    -- Airflow: acces complet (ecriture des donnees depuis les DAGs)
    GRANT ALL ON SCHEMA public TO ${AIRFLOW_DB_USER};
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${AIRFLOW_DB_USER};
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${AIRFLOW_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${AIRFLOW_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${AIRFLOW_DB_USER};

    -- FastAPI: lecture seule sur les donnees de trading
    GRANT CONNECT ON DATABASE ${TRADING_DB_NAME} TO ${FASTAPI_DB_USER};
    GRANT USAGE ON SCHEMA public TO ${FASTAPI_DB_USER};
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO ${FASTAPI_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO ${FASTAPI_DB_USER};

    -- Streamlit: lecture seule sur les donnees de trading
    GRANT CONNECT ON DATABASE ${TRADING_DB_NAME} TO ${STREAMLIT_DB_USER};
    GRANT USAGE ON SCHEMA public TO ${STREAMLIT_DB_USER};
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO ${STREAMLIT_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO ${STREAMLIT_DB_USER};
EOSQL

echo "  [OK] Airflow: lecture/ecriture"
echo "  [OK] FastAPI: lecture seule"
echo "  [OK] Streamlit: lecture seule"

# ============================================================================
# PERMISSIONS SUR LES BASES DE DONNEES DES SERVICES
# ============================================================================

echo ""
echo "[4/4] Configuration des permissions sur les bases des services..."

# Airflow
PGPASSWORD=$POSTGRES_PASSWORD psql -h postgres -U $POSTGRES_USER -d ${AIRFLOW_DB_NAME} <<-EOSQL
    GRANT ALL ON SCHEMA public TO ${AIRFLOW_DB_USER};
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${AIRFLOW_DB_USER};
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${AIRFLOW_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${AIRFLOW_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${AIRFLOW_DB_USER};
EOSQL
echo "  [OK] ${AIRFLOW_DB_NAME}: ${AIRFLOW_DB_USER} a tous les droits"

# MLflow
PGPASSWORD=$POSTGRES_PASSWORD psql -h postgres -U $POSTGRES_USER -d ${MLFLOW_DB_NAME} <<-EOSQL
    GRANT ALL ON SCHEMA public TO ${MLFLOW_DB_USER};
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${MLFLOW_DB_USER};
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${MLFLOW_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${MLFLOW_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${MLFLOW_DB_USER};
EOSQL
echo "  [OK] ${MLFLOW_DB_NAME}: ${MLFLOW_DB_USER} a tous les droits"

# FastAPI
PGPASSWORD=$POSTGRES_PASSWORD psql -h postgres -U $POSTGRES_USER -d ${FASTAPI_DB_NAME} <<-EOSQL
    GRANT ALL ON SCHEMA public TO ${FASTAPI_DB_USER};
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${FASTAPI_DB_USER};
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${FASTAPI_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${FASTAPI_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${FASTAPI_DB_USER};
EOSQL
echo "  [OK] ${FASTAPI_DB_NAME}: ${FASTAPI_DB_USER} a tous les droits"

# ============================================================================
# RESUME
# ============================================================================

echo ""
echo "============================================================================"
echo "Database initialization completed successfully!"
echo "============================================================================"
echo ""
echo "Resume des acces:"
echo ""
echo "  Utilisateur    | Acces"
echo "  ---------------|--------------------------------------------------"
echo "  ${POSTGRES_USER}        | Superuser (toutes les bases)"
echo "  ${AIRFLOW_DB_USER}       | ${AIRFLOW_DB_NAME} (RW) + ${TRADING_DB_NAME} (RW)"
echo "  ${MLFLOW_DB_USER}        | ${MLFLOW_DB_NAME} (RW)"
echo "  ${FASTAPI_DB_USER}       | ${FASTAPI_DB_NAME} (RW) + ${TRADING_DB_NAME} (R)"
echo "  ${STREAMLIT_DB_USER}     | ${TRADING_DB_NAME} (R)"
echo ""
