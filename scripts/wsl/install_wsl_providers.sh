#!/usr/bin/env bash
#
# Install Ollama + LiteLLM inside WSL for Cline multi-provider setup
# - Installs Ollama (if missing)
# - Creates venv and installs litellm[proxy]
# - Prints notes for reusing/copying model cache from Windows

set -euo pipefail

REPO_DIR=$(cd "$(dirname "$0")/../.." && pwd)
cd "$REPO_DIR"

echo "============================================"
echo "Installing WSL providers (Ollama + LiteLLM)"
echo "Repo: $REPO_DIR"
echo "============================================"
echo ""

# 1) Install Ollama if not present
if ! command -v ollama >/dev/null 2>&1; then
  echo "[INFO] Ollama not found. Installing..."
  echo "      (You may be prompted for sudo to install the system service.)"
  curl -fsSL https://ollama.com/install.sh | sh
else
  echo "[OK] Ollama is already installed."
fi

echo ""

# 2) Create Python venv and install LiteLLM proxy
VENV_DIR="venv/llm"
if [ ! -d "$VENV_DIR" ]; then
  echo "[INFO] Creating Python venv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

echo "[INFO] Activating venv and installing litellm[proxy]"
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
python -m pip install "litellm[proxy]"

echo ""
echo "============================================"
echo "WSL providers installed"
echo "============================================"
echo "Notes:"
echo "- To reuse Windows model cache without re-downloading:"
echo "    export OLLAMA_MODELS=/mnt/c/Users/<YourUser>/.ollama/models"
echo "- For best performance, copy models into WSL (ext4):"
echo "    rsync -av --progress /mnt/c/Users/<YourUser>/.ollama/ ~/.ollama/"
echo "- Activate the venv before starting providers:"
echo "    source venv/llm/bin/activate"
echo ""
echo "Next: start providers with:"
echo "    bash start_cline_models.sh"
echo ""

