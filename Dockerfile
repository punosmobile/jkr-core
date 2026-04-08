# Käytä virallista Python 3.11 -slim-kuvaa pohjana
FROM python:3.11-slim

# Aseta ympäristömuuttujat
ENV PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.5.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    APPDATA=/$HOME/.config/jkr/.env

# Asenna järjestelmäriippuvuudet ja QGIS
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    libpq-dev \
    postgresql-client \
    gdal-bin \
    python3-gdal \
    qgis \
    libgdal-dev \
    libspatialindex-dev \
    curl \
    git \
    locales && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Aseta locale
RUN sed -i '/fi_FI.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen
ENV LANG fi_FI.UTF-8
ENV LANGUAGE fi_FI:fi
ENV LC_ALL fi_FI.UTF-8

# Set GDAL configuration paths
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Asenna Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Lisää Poetry PATH:iin
ENV PATH="/root/.local/bin:$PATH"

# Päivitä pip
RUN pip install --upgrade pip

# Varmista /data/input -kansio
RUN mkdir -p /data/input

# Määritä työhakemisto
WORKDIR /app

# Kopioi projektin tiedostot
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --no-dev

COPY . .
RUN poetry install --no-dev

# Avaa API-portti
EXPOSE 8000

# Käynnistä API
CMD ["uvicorn", "jkrimporter.api.api:app", "--host", "0.0.0.0", "--port", "8000"]
