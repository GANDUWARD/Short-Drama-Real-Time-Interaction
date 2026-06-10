#!/usr/bin/env bash
set -euo pipefail
export CUDA_VISIBLE_DEVICES=1
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

CONDA_ENV="${CONDA_ENV:-highlight}"
MODEL_PATH="${MODEL_PATH:-/raid/chenjiahao/model/highlight-ft-qvhighlights}"
VIDEO_PATH="${VIDEO_PATH:-/raid/chenjiahao/datasets/vedios/download.mp4}"
OUTPUT_JSON="${OUTPUT_JSON:-${REPO_ROOT}/outputs/download_qvhighlights_result.json}"
QUERY="${QUERY:-A childhood scene where creditors came to the door and sparked a conflict.}"
NUM_FRAMES="${NUM_FRAMES:-8}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-512}"
DEVICE="${DEVICE:-cuda}"

if [[ -z "${QUERY}" ]]; then
  echo "QUERY is required."
  echo "Example:"
  echo "  QUERY='the person is speaking to the camera' bash ${BASH_SOURCE[0]}"
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
  --num-frames "${NUM_FRAMES}" \
  --max-new-tokens "${MAX_NEW_TOKENS}" \
  --device "${DEVICE}"
