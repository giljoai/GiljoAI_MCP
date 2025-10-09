#!/usr/bin/env bash
#
# Start Cline Models - Linux/WSL Native Version
#
# This starts:
# 1. llama3.1:70b on GPU0 at http://127.0.0.1:11434 (Ollama provider for Cline)
# 2. qwen2.5-coder:32b on GPU1 at http://127.0.0.1:11435 (backend for LiteLLM)
# 3. LiteLLM proxy at http://127.0.0.1:11436/v1 (OpenAI provider for Cline)

echo "============================================"
echo "Starting Models for Cline Multi-Provider"
echo "============================================"
echo ""
echo "Provider 1 (Ollama): llama3.1:70b"
echo "Provider 2 (OpenAI via LiteLLM): qwen2.5-coder:32b"
echo ""

# Start llama3.1:70b on GPU0 in background
echo "Starting Llama 70B (GPU0)..."
python /mnt/f/startOllama.py --single-model &
LLAMA_PID=$!

# Wait for it to warm up
echo "Waiting 10 seconds for Llama to start..."
sleep 10

# Start qwen2.5-coder on GPU1 (port 11435) in background
echo "Starting Qwen 32B (GPU1)..."
CUDA_VISIBLE_DEVICES=1 OLLAMA_HOST=127.0.0.1:11435 ollama serve &
QWEN_PID=$!

# Wait for qwen to start
echo "Waiting 10 seconds for Qwen to start..."
sleep 10

# Start LiteLLM proxy for qwen model in background
echo "Starting LiteLLM Proxy..."
python /mnt/f/lite.py \
    --executor-model qwen2.5-coder:32b \
    --executor-url http://127.0.0.1:11435 \
    --port 11436 \
    --api-key sk-giljo-local &
LITELLM_PID=$!

echo ""
echo "============================================"
echo "All servers starting..."
echo "============================================"
echo ""
echo "Process IDs:"
echo "  Llama 70B:  $LLAMA_PID"
echo "  Qwen 32B:   $QWEN_PID"
echo "  LiteLLM:    $LITELLM_PID"
echo ""
echo "Cline Configuration:"
echo ""
echo "Provider 1 - Ollama:"
echo "  Base URL: http://127.0.0.1:11434"
echo "  Model: llama3.1:70b"
echo ""
echo "Provider 2 - OpenAI:"
echo "  Base URL: http://127.0.0.1:11436/v1"
echo "  API Key: sk-giljo-local"
echo "  Model: qwen2.5-coder:32b"
echo ""
echo "============================================"
echo ""
echo "To verify servers are running:"
echo "  • Llama 70B:  curl http://localhost:11434/api/tags"
echo "  • Qwen 32B:   curl http://localhost:11435/api/tags"
echo "  • LiteLLM:    curl http://localhost:11436/v1/models"
echo ""
echo "To stop all servers:"
echo "  kill $LLAMA_PID $QWEN_PID $LITELLM_PID"
echo ""
