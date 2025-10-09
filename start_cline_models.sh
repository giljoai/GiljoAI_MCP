#!/usr/bin/env bash
#
# Start Cline Models - WSL/Linux Native (no Windows dependencies)
#
# Runs two Ollama endpoints and a LiteLLM proxy inside WSL:
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

# --- Pre-flight checks ---
if ! command -v ollama >/dev/null 2>&1; then
  echo "[ERROR] 'ollama' not found in WSL. Install with:"
  echo "  curl -fsSL https://ollama.com/install.sh | sh"
  exit 1
fi

if ! python3 -c "import litellm" >/dev/null 2>&1; then
  echo "[WARN] Python 'litellm' proxy not found. If you ran scripts/wsl/install_wsl_providers.sh,"
  echo "      activate the venv: 'source venv/llm/bin/activate' or install:"
  echo "      python3 -m venv venv/llm && source venv/llm/bin/activate && pip install 'litellm[proxy]'"
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

# Helper: check if port is in use
port_in_use() {
  ss -lnt 2>/dev/null | awk '{print $4}' | grep -q ":$1$" || return 1
}

# Helper: create temp config folder
mkdir -p "${REPO_DIR}/temp"

# Start Planner Ollama (llama3.1:70b) on 127.0.0.1:11434
if port_in_use "$PORT_PLAN"; then
  echo "[ERROR] Port $PORT_PLAN already in use. Stop the process using it and retry."
  exit 1
fi

echo "Starting Planner (Ollama - llama3.1:70b) on :$PORT_PLAN ..."
if [ "$GPU_COUNT" -ge 1 ]; then
  CUDA_VISIBLE_DEVICES=0 OLLAMA_HOST=127.0.0.1:${PORT_PLAN} ollama serve &
else
  OLLAMA_HOST=127.0.0.1:${PORT_PLAN} ollama serve &
fi
LLAMA_PID=$!

sleep 3

# Start Executor Ollama (qwen) if >= 2 GPUs; else reuse Planner port
EXECUTOR_URL="http://127.0.0.1:${PORT_PLAN}"
QWEN_PID=""
if [ "$GPU_COUNT" -ge 2 ]; then
  if port_in_use "$PORT_EXEC_OLLAMA"; then
    echo "[ERROR] Port $PORT_EXEC_OLLAMA already in use. Stop the process using it and retry."
    kill "$LLAMA_PID" >/dev/null 2>&1 || true
    exit 1
  fi
  echo "Starting Executor (Ollama - qwen2.5-coder:32b) on :$PORT_EXEC_OLLAMA ..."
  CUDA_VISIBLE_DEVICES=1 OLLAMA_HOST=127.0.0.1:${PORT_EXEC_OLLAMA} ollama serve &
  QWEN_PID=$!
  EXECUTOR_URL="http://127.0.0.1:${PORT_EXEC_OLLAMA}"
else
  echo "[INFO] Single GPU or no GPU detected. Reusing Planner Ollama at :$PORT_PLAN for Executor."
fi

sleep 3

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
  echo "[ERROR] Port $PORT_LITELLM already in use. Stop the process using it and retry."
  kill "$LLAMA_PID" >/dev/null 2>&1 || true
  if [ -n "$QWEN_PID" ]; then kill "$QWEN_PID" >/dev/null 2>&1 || true; fi
  exit 1
fi

echo "Starting LiteLLM Proxy on :$PORT_LITELLM ..."
trap 'echo; echo "Stopping services..."; kill $LLAMA_PID >/dev/null 2>&1 || true; if [ -n "$QWEN_PID" ]; then kill $QWEN_PID >/dev/null 2>&1 || true; fi' EXIT

python -m litellm.proxy \
  --host 127.0.0.1 \
  --port ${PORT_LITELLM} \
  --config "$LITELLM_CONFIG_PATH"

echo ""
echo "============================================"
echo "All servers started"
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
if [ -n "$QWEN_PID" ]; then
  echo "  curl http://127.0.0.1:${PORT_EXEC_OLLAMA}/api/tags"
fi
echo "  curl http://127.0.0.1:${PORT_LITELLM}/v1/models -H 'Authorization: Bearer sk-giljo-local'"
echo ""

