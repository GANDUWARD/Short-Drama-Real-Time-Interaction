#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

CONDA_ENV="${CONDA_ENV:-highlight}"
MODEL_PATH="${MODEL_PATH:-/raid/chenjiahao/model/highlight-ft-qvhighlights}"
VIDEO_PATH="${VIDEO_PATH:-/raid/chenjiahao/datasets/vedios/download.mp4}"
OUTPUT_JSON="${OUTPUT_JSON:-${REPO_ROOT}/outputs/download_qvhighlights_with_caption_result.json}"
PROMPT_TEMPLATE_FILE="${PROMPT_TEMPLATE_FILE:-${SCRIPT_DIR}/qvhighlights_with_caption_prompt.txt}"
QUERY="${QUERY:-}"
NUM_FRAMES="${NUM_FRAMES:-128}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-768}"
DEVICE="${DEVICE:-cuda}"

if [[ -z "${QUERY}" ]]; then
  echo "QUERY is required."
  echo "Example:"
  echo "  QUERY='A childhood scene where creditors came to the door and sparked a conflict.' bash ${BASH_SOURCE[0]}"
  exit 1
fi

if ! command -v conda >/dev/null 2>&1; then
  echo "conda is not in PATH. Please initialize conda first."
  exit 1
fi

CONDA_BASE="$(conda info --base)"
source "${CONDA_BASE}/etc/profile.d/conda.sh"
conda activate "${CONDA_ENV}"

mkdir -p "$(dirname -- "${OUTPUT_JSON}")"

cd "${REPO_ROOT}"
python3 scripts/inference/run_highlight_qvhighlights.py \
  --model-path "${MODEL_PATH}" \
  --video-path "${VIDEO_PATH}" \
  --query "${QUERY}" \
  --output-json "${OUTPUT_JSON}" \
  --prompt-template-file "${PROMPT_TEMPLATE_FILE}" \
  --num-frames "${NUM_FRAMES}" \
  --max-new-tokens "${MAX_NEW_TOKENS}" \
  --device "${DEVICE}"
