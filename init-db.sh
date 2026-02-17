#!/bin/bash
set -e

# Les variables sont passées depuis le docker-compose via environment
AIRFLOW_DB_NAME="${AIRFLOW_DB_NAME:-airflow}"
AIRFLOW_DB_USER="${AIRFLOW_DB_USER:-airflow}"
AIRFLOW_DB_PASSWORD="${AIRFLOW_DB_PASSWORD:-airflow}"
MLFLOW_DB_NAME="${MLFLOW_DB_NAME:-mlflow}"
MLFLOW_DB_USER="${MLFLOW_DB_USER:-mlflow}"
MLFLOW_DB_PASSWORD="${MLFLOW_DB_PASSWORD:-mlflow}"

echo "Starting database initialization..."

# Créer les utilisateurs et bases de données
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Créer les utilisateurs
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '${AIRFLOW_DB_USER}') THEN
            CREATE USER ${AIRFLOW_DB_USER} WITH PASSWORD '${AIRFLOW_DB_PASSWORD}';
            RAISE NOTICE 'User ${AIRFLOW_DB_USER} created';
        ELSE
            RAISE NOTICE 'User ${AIRFLOW_DB_USER} already exists';
        END IF;

        IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '${MLFLOW_DB_USER}') THEN
            CREATE USER ${MLFLOW_DB_USER} WITH PASSWORD '${MLFLOW_DB_PASSWORD}';
            RAISE NOTICE 'User ${MLFLOW_DB_USER} created';
        ELSE
            RAISE NOTICE 'User ${MLFLOW_DB_USER} already exists';
        END IF;
    END
    \$\$;

    -- Créer les bases de données
    SELECT 'CREATE DATABASE ${AIRFLOW_DB_NAME} OWNER ${AIRFLOW_DB_USER}'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${AIRFLOW_DB_NAME}')\gexec

    SELECT 'CREATE DATABASE ${MLFLOW_DB_NAME} OWNER ${MLFLOW_DB_USER}'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${MLFLOW_DB_NAME}')\gexec
EOSQL

echo "Granting permissions for Airflow database..."
# Connexion à la base Airflow pour accorder les permissions
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "${AIRFLOW_DB_NAME}" <<-EOSQL
    GRANT ALL ON SCHEMA public TO ${AIRFLOW_DB_USER};
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${AIRFLOW_DB_USER};
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${AIRFLOW_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${AIRFLOW_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${AIRFLOW_DB_USER};
EOSQL

echo "Granting permissions for MLflow database..."
# Connexion à la base MLflow pour accorder les permissions
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "${MLFLOW_DB_NAME}" <<-EOSQL
    GRANT ALL ON SCHEMA public TO ${MLFLOW_DB_USER};
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${MLFLOW_DB_USER};
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${MLFLOW_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${MLFLOW_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${MLFLOW_DB_USER};
EOSQL

echo "Database initialization completed successfully!"