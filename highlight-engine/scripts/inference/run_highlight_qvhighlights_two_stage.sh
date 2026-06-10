#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

CONDA_ENV="${CONDA_ENV:-highlight}"
MODEL_PATH="${MODEL_PATH:-/raid/chenjiahao/model/highlight-ft-qvhighlights}"
STAGE2_MODEL_PATH="${STAGE2_MODEL_PATH:-$MODEL_PATH}"
STAGE2_BACKEND="${STAGE2_BACKEND:-highlight}"
VIDEO_PATH="${VIDEO_PATH:-/raid/chenjiahao/datasets/vedios/download.mp4}"
OUTPUT_JSON="${OUTPUT_JSON:-${REPO_ROOT}/outputs/download_qvhighlights_two_stage_result.json}"
QUERY="${QUERY:-}"
DEVICE="${DEVICE:-cuda}"
DETECT_NUM_FRAMES="${DETECT_NUM_FRAMES:-128}"
DESCRIBE_NUM_FRAMES="${DESCRIBE_NUM_FRAMES:-64}"
DETECT_MAX_NEW_TOKENS="${DETECT_MAX_NEW_TOKENS:-512}"
DESCRIBE_MAX_NEW_TOKENS="${DESCRIBE_MAX_NEW_TOKENS:-96}"
MIN_SCORE="${MIN_SCORE:-3.0}"
MERGE_GAP="${MERGE_GAP:-0.75}"
SEGMENT_PADDING="${SEGMENT_PADDING:-1.0}"
MIN_SEGMENT_SECONDS="${MIN_SEGMENT_SECONDS:-2.0}"
MAX_SEGMENTS="${MAX_SEGMENTS:-5}"

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
python3 scripts/inference/run_highlight_qvhighlights_two_stage.py \
  --model-path "${MODEL_PATH}" \
  --stage2-model-path "${STAGE2_MODEL_PATH}" \
  --stage2-backend "${STAGE2_BACKEND}" \
  --video-path "${VIDEO_PATH}" \
  --query "${QUERY}" \
  --output-json "${OUTPUT_JSON}" \
  --device "${DEVICE}" \
  --detect-num-frames "${DETECT_NUM_FRAMES}" \
  --describe-num-frames "${DESCRIBE_NUM_FRAMES}" \
  --detect-max-new-tokens "${DETECT_MAX_NEW_TOKENS}" \
  --describe-max-new-tokens "${DESCRIBE_MAX_NEW_TOKENS}" \
  --min-score "${MIN_SCORE}" \
  --merge-gap "${MERGE_GAP}" \
  --segment-padding "${SEGMENT_PADDING}" \
  --min-segment-seconds "${MIN_SEGMENT_SECONDS}" \
  --max-segments "${MAX_SEGMENTS}"
