FROM python:3.12.7-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gotify2apprise ./gotify2apprise
COPY program.py .
COPY config.example.yaml .

ENV DATA_DIR=/var/lib/gotify2apprise
ENV CONF_FILE=/etc/gotify2apprise/config.yaml
ENV UI_HOST=0.0.0.0
ENV UI_PORT=8080

VOLUME ["/var/lib/gotify2apprise"]
EXPOSE 8080

CMD ["python", "-m", "gotify2apprise.main"]
