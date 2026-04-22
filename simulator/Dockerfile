FROM cr.yandex/mirror/library/python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files from simulator directory into /app/simulator package
COPY . simulator/

# Ensure the parent directory is in PYTHONPATH to allow running as module
ENV PYTHONPATH=/app

# In docker we use 'mosquitto' service name for the broker
ENV MQTT_HOST=mosquitto

CMD ["python", "-m", "simulator.simulator"]
