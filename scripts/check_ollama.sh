cd#!/bin/sh
# Check that Ollama is reachable and the model returns a response (run on host: ./scripts/check_ollama.sh)
# Usage: OLLAMA_HOST=http://localhost:11434 OLLAMA_MODEL=llama3.2:3b-instruct-q4_0 ./scripts/check_ollama.sh

HOST="${OLLAMA_HOST:-http://localhost:11434}"
MODEL="${OLLAMA_MODEL:-llama3.2:1b}"

echo "Checking Ollama at $HOST (model: $MODEL)"
if ! curl -sf "$HOST/api/tags" > /dev/null; then
  echo "FAIL: Cannot reach $HOST (is Ollama running?)"
  exit 1
fi
echo "OK: Ollama reachable"

echo "Requesting one short reply from model (may take 30-90s on CPU)..."
RESP=$(curl -s -X POST "$HOST/api/chat" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"whats your name ?\"}],\"stream\":false,\"options\":{\"num_predict\":5}}" \
  --max-time 120)

if echo "$RESP" | grep -q '"content"'; then
  MSG=$(echo "$RESP" | sed -n 's/.*"content":"\([^"]*\)".*/\1/p' | head -1)
  echo "OK: Model responded: $RESP"
else
  echo "FAIL: No content in response: $RESP"
  exit 1
fi
