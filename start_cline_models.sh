#!/usr/bin/env bash
#
# Start Cline Models - WSL/Linux Native (one-command bootstrap)
#
# Runs two Ollama endpoints and a LiteLLM proxy inside WSL, and
# bootstraps Python venv + LiteLLM if missing:
# 1) Planner:  llama3.1:70b via Ollama at http://127.0.0.1:11434
# 2) Executor: qwen2.5-coder:32b via LiteLLM (OpenAI-compatible) at http://127.0.0.1:11436/v1
#
# Notes:
# - If you have only one GPU, we reuse the single Ollama server (11434) for both models.
# - To reuse Windows model cache without redownloading, export OLLAMA_MODELS to Windows path, e.g.:
#     export OLLAMA_MODELS=/mnt/c/Users/<YourUser>/.ollama/models
# - For best performance, copy models into WSL: rsync -av /mnt/c/Users/<YourUser>/.ollama/ ~/.ollama/

set -euo pipefail

REPO_DIR=$(cd "$(dirname "$0")" && pwd)

echo "============================================"
echo "Starting Models for Cline (WSL Native)"
echo "============================================"
echo ""

have_cmd() { command -v "$1" >/dev/null 2>&1; }

# Auto-install Ollama if missing
if ! have_cmd ollama; then
  echo "[INFO] 'ollama' not found. Attempting install..."
  if have_cmd curl; then
    curl -fsSL https://ollama.com/install.sh | sh || {
      echo "[ERROR] Failed to install Ollama automatically. Install manually and retry."; exit 1; }
  else
    echo "[ERROR] curl not available to install Ollama. Install curl or Ollama and retry."; exit 1
  fi
fi

# Ensure Python venv + LiteLLM are available
if [ ! -d "venv/llm" ]; then
  echo "[INFO] Creating Python venv at venv/llm"
  if ! python3 -m venv venv/llm 2>/dev/null; then
    echo "[INFO] python3-venv not found. Attempting apt install..."
    if have_cmd sudo && have_cmd apt-get; then
      sudo apt-get update -y && sudo apt-get install -y python3-venv || true
    fi
    python3 -m venv venv/llm
  fi
fi
# shellcheck disable=SC1091
source venv/llm/bin/activate
python -m pip install --upgrade pip >/dev/null
if ! have_cmd litellm; then
  echo "[INFO] Installing LiteLLM proxy..."
  python -m pip install "litellm[proxy]" >/dev/null
fi

# Determine GPU count (NVIDIA)
GPU_COUNT=0
if command -v nvidia-smi >/dev/null 2>&1; then
  GPU_COUNT=$(nvidia-smi -L 2>/dev/null | wc -l | xargs || true)
fi

# Ports
PORT_PLAN=11434
PORT_EXEC_OLLAMA=11435
PORT_LITELLM=11436

port_in_use() {
  if have_cmd ss; then
    ss -lnt 2>/dev/null | awk '{print $4}' | grep -q ":$1$" || return 1
  else
    netstat -lnt 2>/dev/null | awk '{print $4}' | grep -q ":$1$" || return 1
  fi
}

wait_for_ollama() {
  local port=$1; local retries=${2:-60}
  for i in $(seq 1 "$retries"); do
    if curl -fsS "http://127.0.0.1:${port}/api/tags" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

pull_if_missing() {
  local port=$1; local model=$2
  if ! OLLAMA_HOST=127.0.0.1:${port} ollama show "$model" >/dev/null 2>&1; then
    echo "[INFO] Pulling model '$model' on :$port (this may take a while)..."
    OLLAMA_HOST=127.0.0.1:${port} ollama pull "$model"
  fi
}

# Helper: create temp config folder
mkdir -p "${REPO_DIR}/temp"

LLAMA_PID=""
if port_in_use "$PORT_PLAN"; then
  echo "[INFO] Port $PORT_PLAN in use - reusing existing Ollama server."
else
  echo "Starting Planner (Ollama - llama3.1:70b) on :$PORT_PLAN ..."
  if [ "$GPU_COUNT" -ge 1 ]; then
    CUDA_VISIBLE_DEVICES=0 OLLAMA_HOST=127.0.0.1:${PORT_PLAN} ollama serve &
  else
    OLLAMA_HOST=127.0.0.1:${PORT_PLAN} ollama serve &
  fi
  LLAMA_PID=$!
fi

if ! wait_for_ollama "$PORT_PLAN" 60; then
  echo "[ERROR] Planner Ollama on :$PORT_PLAN did not become ready."; exit 1
fi

# Ensure planner model exists
pull_if_missing "$PORT_PLAN" "llama3.1:70b"

# Start Executor Ollama (qwen) if >= 2 GPUs; else reuse Planner port
EXECUTOR_URL="http://127.0.0.1:${PORT_PLAN}"
QWEN_PID=""
if [ "$GPU_COUNT" -ge 2 ]; then
  if port_in_use "$PORT_EXEC_OLLAMA"; then
    echo "[INFO] Port $PORT_EXEC_OLLAMA in use - reusing existing Ollama for executor."
  else
    echo "Starting Executor (Ollama - qwen2.5-coder:32b) on :$PORT_EXEC_OLLAMA ..."
    CUDA_VISIBLE_DEVICES=1 OLLAMA_HOST=127.0.0.1:${PORT_EXEC_OLLAMA} ollama serve &
    QWEN_PID=$!
  fi
  EXECUTOR_URL="http://127.0.0.1:${PORT_EXEC_OLLAMA}"
  if ! wait_for_ollama "$PORT_EXEC_OLLAMA" 60; then
    echo "[ERROR] Executor Ollama on :$PORT_EXEC_OLLAMA did not become ready."; exit 1
  fi
else
  echo "[INFO] Single GPU or no GPU detected. Reusing Planner Ollama at :$PORT_PLAN for Executor."
fi

# Ensure executor model exists (on whichever server is used)
pull_if_missing "${EXECUTOR_URL##*:}" "qwen2.5-coder:32b"

# Generate LiteLLM config pointing to the Executor URL
LITELLM_CONFIG_PATH="${REPO_DIR}/temp/litellm_wsl.generated.yaml"
cat > "$LITELLM_CONFIG_PATH" <<YAML
model_list:
  - model_name: qwen2.5-coder:32b
    litellm_params:
      model: ollama/qwen2.5-coder:32b
      api_base: ${EXECUTOR_URL}
      api_key: sk-giljo-local
YAML

# Start LiteLLM proxy on 127.0.0.1:11436/v1
if port_in_use "$PORT_LITELLM"; then
  echo "[INFO] Port $PORT_LITELLM in use - another LiteLLM may be running. Reusing it."
else
  echo "Starting LiteLLM Proxy on :$PORT_LITELLM ..."
  trap 'echo; echo "Stopping services..."; [ -n "$LLAMA_PID" ] && kill $LLAMA_PID >/dev/null 2>&1 || true; [ -n "$QWEN_PID" ] && kill $QWEN_PID >/dev/null 2>&1 || true' EXIT
  if command -v litellm >/dev/null 2>&1; then
    litellm --host 127.0.0.1 --port ${PORT_LITELLM} --config "$LITELLM_CONFIG_PATH"
  else
    python -m uvicorn litellm.proxy.proxy_server:app --host 127.0.0.1 --port ${PORT_LITELLM} --log-level info
  fi
fi

echo ""
echo "============================================"
echo "All servers ready"
echo "============================================"
echo ""
echo "Process IDs:"
echo "  Planner (llama): $LLAMA_PID"
if [ -n "$QWEN_PID" ]; then
  echo "  Executor (qwen): $QWEN_PID"
else
  echo "  Executor (qwen): reusing Planner server"
fi
echo "  LiteLLM:        (foreground)"
echo ""
echo "Cline Configuration:"
echo "  Provider 1 - Ollama (Planner):"
echo "    Base URL: http://127.0.0.1:${PORT_PLAN}"
echo "    Model:    llama3.1:70b"
echo ""
echo "  Provider 2 - OpenAI (Executor via LiteLLM):"
echo "    Base URL: http://127.0.0.1:${PORT_LITELLM}/v1"
echo "    API Key:  sk-giljo-local"
echo "    Model:    qwen2.5-coder:32b"
echo ""
echo "Verify:"
echo "  curl http://127.0.0.1:${PORT_PLAN}/api/tags"
if [ "$EXECUTOR_URL" != "http://127.0.0.1:${PORT_PLAN}" ]; then
  echo "  curl ${EXECUTOR_URL}/api/tags"
fi
echo "  curl http://127.0.0.1:${PORT_LITELLM}/v1/models -H 'Authorization: Bearer sk-giljo-local'"
echo ""
