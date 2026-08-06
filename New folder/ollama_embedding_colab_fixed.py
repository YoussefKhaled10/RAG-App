# -*- coding: utf-8 -*-
"""Ollama Embedding Server for Colab - pure Python version.

This file avoids Colab shell magics like !curl and %%bash, so it can run as
normal Python in Colab. It installs Ollama, starts an Ollama server, pulls
nomic-embed-text, tests /api/embed, exposes the server through ngrok, and
prints the .env.app values for your RAG app.

Recommended .env.app output:
EMBEDDING_BACKEND=OLLAMA
OLLAMA_API_URL=<printed_ngrok_url>
EMBEDDING_MODEL_ID=nomic-embed-text
EMBEDDING_MODEL_SIZE=768
"""

import os
import time
import subprocess
import requests


def run(cmd, check=True):
    print(f"\n[RUN] {cmd}")
    return subprocess.run(cmd, shell=True, check=check)


# =========================
# System dependencies
# =========================
run("apt-get update")
run("apt-get install -y zstd curl jq")


# =========================
# Install Ollama
# =========================
run("curl -fsSL https://ollama.com/install.sh | sh")


# =========================
# Ollama settings
# =========================
OLLAMA_MODEL_ID = "nomic-embed-text"
OLLAMA_PORT = 11501
OLLAMA_BASE_URL = f"http://127.0.0.1:{OLLAMA_PORT}"


# Stop old Ollama process if any
run("pkill -f ollama || true", check=False)


# Start Ollama server
log_file = "/content/nohup.out"
cmd = (
    f"OLLAMA_HOST=0.0.0.0:{OLLAMA_PORT} "
    f"OLLAMA_ORIGINS=* "
    f"nohup ollama serve > {log_file} 2>&1 &"
)
run(cmd)


# Wait for server
print("\nWaiting for Ollama server...")
time.sleep(8)
run(f"tail -n 50 {log_file}", check=False)


# Check server
print("\nChecking Ollama tags...")
resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=30)
print(resp.status_code)
print(resp.text[:1000])


# Pull embedding model
run(f"OLLAMA_HOST={OLLAMA_BASE_URL} ollama pull {OLLAMA_MODEL_ID}")


# Check installed models
resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=30)
print("\nInstalled models:")
print(resp.text[:2000])


# Test local embedding endpoint
print("\nTesting local /api/embed...")
resp = requests.post(
    f"{OLLAMA_BASE_URL}/api/embed",
    json={
        "model": OLLAMA_MODEL_ID,
        "input": ["This is a test sentence for embeddings."],
    },
    timeout=120,
)
print("Status:", resp.status_code)
resp.raise_for_status()
embedding = resp.json()["embeddings"][0]
print("Embedding size:", len(embedding))


# =========================
# Install and configure ngrok
# =========================
run("pip install pyngrok")

from pyngrok import ngrok, conf

try:
    from google.colab import userdata
    ngrok_auth = userdata.get("ngrok")
except Exception:
    ngrok_auth = os.environ.get("NGROK_AUTH_TOKEN")

if not ngrok_auth:
    raise RuntimeError(
        "ngrok token not found. In Colab, add a secret named 'ngrok'. "
        "Or set NGROK_AUTH_TOKEN environment variable."
    )

conf.get_default().auth_token = ngrok_auth

public_url = ngrok.connect(str(OLLAMA_PORT)).public_url
print("\nOllama public URL:", public_url)


# Test public embedding endpoint
print("\nTesting public ngrok /api/embed...")
resp = requests.post(
    f"{public_url}/api/embed",
    json={
        "model": OLLAMA_MODEL_ID,
        "input": ["Hello from ngrok Ollama embedding server."],
    },
    timeout=120,
)
print("Status:", resp.status_code)
resp.raise_for_status()
embedding = resp.json()["embeddings"][0]
print("Embedding size:", len(embedding))


# Print env values
print("\n==============================")
print("Use these values in docker/env/.env.app")
print("==============================")
print("EMBEDDING_BACKEND=OLLAMA")
print(f"OLLAMA_API_URL={public_url}")
print(f"EMBEDDING_MODEL_ID={OLLAMA_MODEL_ID}")
print("EMBEDDING_MODEL_SIZE=768")


# Logs
print("\nOllama logs:")
run(f"tail -n 100 {log_file}", check=False)
