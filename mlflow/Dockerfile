FROM python:3.11-slim

WORKDIR /mlflow

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    mlflow==2.19.0 \
    psycopg2-binary==2.9.9

# Désactiver la vérification du Host header pour éviter les erreurs 403
ENV MLFLOW_HOST="*"

EXPOSE 5000

CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000"]
