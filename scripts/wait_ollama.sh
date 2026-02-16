#!/bin/sh
# Wait for Ollama to be ready (used by app container entrypoint)
until curl -sf http://host.docker.internal:11434/api/tags > /dev/null 2>&1; do
  echo "Waiting for Ollama..."
  sleep 2
done
echo "Ollama is ready."
