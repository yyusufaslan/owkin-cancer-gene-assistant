"""Configuration from environment variables."""
import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
# 3B instruct Q4_K_M - good balance of quality and speed for CPU.
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
LOG_DIR = os.getenv("LOG_DIR", "logs")
