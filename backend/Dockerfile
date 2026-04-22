FROM cr.yandex/mirror/library/python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    DJANGO_SETTINGS_MODULE=telemetry_core.settings

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install uvloop gunicorn daphne

# Copy requirements from backend folder
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

# Copy backend code (including its pyproject.toml)
COPY backend/ .

# Copy tests folder to /app/tests
COPY tests/ ./tests/

# Copy root config files
COPY pytest.ini .

RUN dos2unix init.sh && chmod +x init.sh

ENTRYPOINT ["./init.sh"]

