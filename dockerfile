FROM python:3.9-slim

# Installer les dépendances nécessaires pour les locales
RUN apt-get update && \
    apt-get install -y --no-install-recommends locales && \
    echo "fr_FR.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Définir les variables d'environnement pour la locale
ENV LANG=fr_FR.UTF-8
ENV LANGUAGE=fr_FR.UTF-8
ENV LC_ALL=fr_FR.UTF-8

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt



COPY . .

CMD ["python", "app.py"]