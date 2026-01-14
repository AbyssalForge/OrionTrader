FROM python:3.12-slim

WORKDIR /app

# Installer dépendances système nécessaires pour psycopg2
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copier requirements FastAPI
COPY requirements.txt /app/requirements.txt

# Installer les dépendances FastAPI
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copier ton code FastAPI
COPY . /app

# Rendre le script d'entrée exécutable
RUN chmod +x /app/entrypoint.sh

# Démarrer Uvicorn via entrypoint
# Mode développement: docker run -e ENVIRONMENT=development ...
# Mode production: docker run (par défaut)
ENTRYPOINT ["/app/entrypoint.sh"]
