FROM python:3.12-slim

WORKDIR /app

# Installer dépendances système (optionnel mais utile)
RUN apt-get update && apt-get install -y build-essential && apt-get clean

# Copier requirements FastAPI
COPY requirements.txt /app/requirements.txt

# Installer les dépendances FastAPI
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copier ton code FastAPI
COPY . /app

# Démarrer Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
