# -*- coding: utf-8 -*-
"""Ollama Embedding Server - Colab

This notebook/script starts an Ollama server on Google Colab,
pulls an embedding model, tests /api/embed, and exposes the server via ngrok.

Recommended embedding model:
- nomic-embed-text  -> embedding size usually 768

Use the public ngrok URL as OLLAMA_API_URL in your RAG app.
Example:
OLLAMA_API_URL=https://xxxx.ngrok-free.app
EMBEDDING_BACKEND=OLLAMA
EMBEDDING_MODEL_ID=nomic-embed-text
EMBEDDING_MODEL_SIZE=768
"""

# =========================
# System dependencies
# =========================
!apt-get update
!apt-get install -y zstd curl jq

# =========================
# Install Ollama
# =========================
!curl -fsSL https://ollama.com/install.sh | sh

# =========================
# Ollama settings
# =========================
ollama_model_id = "nomic-embed-text"
ollama_port = 11501

# Stop any old Ollama process
!pkill -f "ollama" || true

# Start Ollama server
!nohup bash -c "OLLAMA_HOST=0.0.0.0:11501 OLLAMA_ORIGINS=* ollama serve" > /content/nohup.out 2>&1 &

# Wait and show logs
!sleep 5 && tail -n 50 /content/nohup.out

# Check Ollama server
!curl http://127.0.0.1:11501/api/tags

# =========================
# Pull embedding model
# =========================
!OLLAMA_HOST=http://127.0.0.1:11501 ollama pull nomic-embed-text

# Check installed models
!curl http://127.0.0.1:11501/api/tags

# =========================
# Test embedding endpoint
# =========================
!curl -s http://127.0.0.1:11501/api/embed \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nomic-embed-text",
    "input": ["This is a test sentence for embeddings."]
  }' | jq '.embeddings[0] | length'

# Expected output is usually 768

# =========================
# Install and configure ngrok
# =========================
!pip install pyngrok

from google.colab import userdata
from pyngrok import ngrok, conf

# Make sure you added your ngrok token in Colab secrets with name: ngrok
ngrok_auth = userdata.get("ngrok")
conf.get_default().auth_token = ngrok_auth

port = "11501"
public_url = ngrok.connect(port).public_url
print("Ollama public URL:", public_url)

# =========================
# Test public embedding endpoint
# =========================
# Replace the URL below with the printed public_url if needed.
# This test runs dynamically using Python requests.

import requests

response = requests.post(
    f"{public_url}/api/embed",
    json={
        "model": "nomic-embed-text",
        "input": ["Hello from ngrok Ollama embedding server."]
    },
    timeout=120
)

print("Status:", response.status_code)
print("Embedding size:", len(response.json()["embeddings"][0]))

# =========================
# Print env values for your RAG app
# =========================
print("\nUse these values in your .env.app:\n")
print("EMBEDDING_BACKEND=OLLAMA")
print(f"OLLAMA_API_URL={public_url}")
print("EMBEDDING_MODEL_ID=nomic-embed-text")
print("EMBEDDING_MODEL_SIZE=768")

# =========================
# Logs
# =========================
!tail -n 100 /content/nohup.out
