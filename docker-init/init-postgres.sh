#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."
# Le healthcheck garantit que postgres est prêt, mais on ajoute une vérification rapide
max_attempts=60
attempt=0

until PGPASSWORD=$POSTGRES_PASSWORD psql -h postgres -U $POSTGRES_USER -d $POSTGRES_DB -c '\q' 2>/dev/null; do
  attempt=$((attempt + 1))
  if [ $attempt -ge $max_attempts ]; then
    echo "ERROR: PostgreSQL did not become ready in time"
    exit 1
  fi
  echo "PostgreSQL is unavailable - attempt $attempt/$max_attempts"
  sleep 1
done

echo "PostgreSQL is up - executing database initialization"

# Créer les utilisateurs et bases de données
PGPASSWORD=$POSTGRES_PASSWORD psql -h postgres -U $POSTGRES_USER -d $POSTGRES_DB <<-EOSQL
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
PGPASSWORD=$POSTGRES_PASSWORD psql -h postgres -U $POSTGRES_USER -d ${AIRFLOW_DB_NAME} <<-EOSQL
    GRANT ALL ON SCHEMA public TO ${AIRFLOW_DB_USER};
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${AIRFLOW_DB_USER};
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${AIRFLOW_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${AIRFLOW_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${AIRFLOW_DB_USER};
EOSQL

echo "Granting permissions for MLflow database..."
PGPASSWORD=$POSTGRES_PASSWORD psql -h postgres -U $POSTGRES_USER -d ${MLFLOW_DB_NAME} <<-EOSQL
    GRANT ALL ON SCHEMA public TO ${MLFLOW_DB_USER};
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${MLFLOW_DB_USER};
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${MLFLOW_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${MLFLOW_DB_USER};
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${MLFLOW_DB_USER};
EOSQL

echo "Database initialization completed successfully!"
