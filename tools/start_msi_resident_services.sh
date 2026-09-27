#!/usr/bin/env bash
set -euo pipefail

# Run on the validated brokeass-msi host as user rey.  The specialist models
# remain resident on CPU; Gemma remains resident in the RTX 3060 via llama.cpp.
SERVICE_DIR=/home/rey/mneme-tools
PYTHON=/home/rey/mneme-extractor-venv/bin/python3
LLAMA=/home/rey/src/llama.cpp/build-cuda/bin/llama-server
MODEL=/home/rey/models/gemma4/gemma-4-E4B-it-qat-UD-Q2_K_XL.gguf
mkdir -p "$SERVICE_DIR/logs"

nohup env CUDA_VISIBLE_DEVICES= "$PYTHON" "$SERVICE_DIR/msi_resident_server.py" \
  --role nli --host 0.0.0.0 --port 64172 \
  > "$SERVICE_DIR/logs/nli.log" 2>&1 < /dev/null &
nohup env CUDA_VISIBLE_DEVICES= "$PYTHON" "$SERVICE_DIR/msi_resident_server.py" \
  --role gliner --host 0.0.0.0 --port 64171 \
  > "$SERVICE_DIR/logs/gliner.log" 2>&1 < /dev/null &
nohup "$LLAMA" -m "$MODEL" --host 0.0.0.0 --port 64170 \
  -c 4096 -ngl 99 --cache-ram 256 --no-cache-idle-slots \
  --no-cont-batching --no-webui --reasoning off --parallel 1 \
  > "$SERVICE_DIR/logs/gemma-server.log" 2>&1 < /dev/null &
