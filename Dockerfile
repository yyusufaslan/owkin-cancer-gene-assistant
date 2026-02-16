FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config/ config/
COPY app/ app/
COPY ui/ ui/
COPY owkin_take_home_data.csv .
COPY scripts/ scripts/

RUN chmod +x scripts/wait_ollama.sh

ENV OLLAMA_BASE_URL=http://host.docker.internal:11434
ENV OLLAMA_MODEL=llama3.2:3b
ENV LOG_DIR=/app/logs

EXPOSE 8000

ENTRYPOINT ["/bin/sh", "-c", "scripts/wait_ollama.sh && chainlit run ui/app.py --port 8000 --host 0.0.0.0"]
