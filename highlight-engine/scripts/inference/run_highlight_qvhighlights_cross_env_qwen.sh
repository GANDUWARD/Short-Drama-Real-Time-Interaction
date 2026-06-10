#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

STAGE1_ENV="${STAGE1_ENV:-highlight}"
STAGE2_ENV="${STAGE2_ENV:-new}"
MODEL_PATH="${MODEL_PATH:-/raid/chenjiahao/model/highlight-ft-qvhighlights}"
STAGE2_MODEL_PATH="${STAGE2_MODEL_PATH:-/raid/chenjiahao/model/Qwen2.5-VL-3B}"
VIDEO_PATH="${VIDEO_PATH:-/raid/chenjiahao/datasets/vedios/download.mp4}"
OUTPUT_JSON="${OUTPUT_JSON:-${REPO_ROOT}/outputs/download_qvhighlights_cross_env_qwen_result.json}"
QUERY="${QUERY:-}"
DEVICE="${DEVICE:-cuda}"
DETECT_NUM_FRAMES="${DETECT_NUM_FRAMES:-128}"
DESCRIBE_MAX_NEW_TOKENS="${DESCRIBE_MAX_NEW_TOKENS:-96}"
MIN_SCORE="${MIN_SCORE:-3.0}"
MERGE_GAP="${MERGE_GAP:-0.75}"
SEGMENT_PADDING="${SEGMENT_PADDING:-1.0}"
MIN_SEGMENT_SECONDS="${MIN_SEGMENT_SECONDS:-2.0}"
MAX_SEGMENTS="${MAX_SEGMENTS:-5}"
KEEP_TEMP_CLIPS="${KEEP_TEMP_CLIPS:-false}"

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

mkdir -p "$(dirname -- "${OUTPUT_JSON}")"
STAGE1_JSON="${OUTPUT_JSON%.json}_stage1.json"

cd "${REPO_ROOT}"

conda activate "${STAGE1_ENV}"
python3 scripts/inference/run_highlight_qvhighlights_two_stage.py \
  --model-path "${MODEL_PATH}" \
  --stage2-model-path "${MODEL_PATH}" \
  --stage2-backend none \
  --video-path "${VIDEO_PATH}" \
  --query "${QUERY}" \
  --output-json "${STAGE1_JSON}" \
  --device "${DEVICE}" \
  --detect-num-frames "${DETECT_NUM_FRAMES}" \
  --describe-num-frames 64 \
  --detect-max-new-tokens 512 \
  --describe-max-new-tokens "${DESCRIBE_MAX_NEW_TOKENS}" \
  --min-score "${MIN_SCORE}" \
  --merge-gap "${MERGE_GAP}" \
  --segment-padding "${SEGMENT_PADDING}" \
  --min-segment-seconds "${MIN_SEGMENT_SECONDS}" \
  --max-segments "${MAX_SEGMENTS}" \
  --keep-temp-clips

conda activate "${STAGE2_ENV}"
STAGE2_ARGS=(
  --model-path "${STAGE2_MODEL_PATH}"
  --stage1-json "${STAGE1_JSON}"
  --output-json "${OUTPUT_JSON}"
  --device "${DEVICE}"
  --max-new-tokens "${DESCRIBE_MAX_NEW_TOKENS}"
)

if [[ "${KEEP_TEMP_CLIPS}" == "true" ]]; then
  STAGE2_ARGS+=(--keep-temp-clips)
fi

python3 scripts/inference/run_qwen2_5_vl_caption_segments.py "${STAGE2_ARGS[@]}"
