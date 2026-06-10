#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

import torch


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from highlight.constants import DEFAULT_MMODAL_TOKEN
from highlight.conversation import conv_templates
from highlight.mm_utils import get_model_name_from_path, process_video, tokenizer_MMODAL_token_all
from highlight.model.builder import load_pretrained_model


DEFAULT_PROMPT_TEMPLATE = (
    "Please find the highlight contents in the video described by a sentence query, "
    "determining the highlight timestamps and its saliency score on a scale from 1 to 5. "
    "Now I will give you the sentence query: '{}'. "
    "Please return the query-based highlight timestamps and salient scores."
)


def parse_args():
    parser = argparse.ArgumentParser(description="Run Highlight QVHighlights inference on a single video.")
    parser.add_argument("--model-path", required=True, help="Path to the local highlight model directory.")
    parser.add_argument("--video-path", required=True, help="Path to the input video.")
    parser.add_argument("--query", required=True, help="Sentence query for QVHighlights-style highlight detection.")
    parser.add_argument("--output-json", required=True, help="Path to the output JSON file.")
    parser.add_argument("--prompt-template-file", default="", help="Optional prompt template file with one '{}' placeholder.")
    parser.add_argument("--num-frames", type=int, default=None, help="Override the number of sampled frames.")
    parser.add_argument("--max-new-tokens", type=int, default=512, help="Maximum number of generated tokens.")
    parser.add_argument("--device", default="cuda", help="Device to run on, usually 'cuda' or 'cpu'.")
    return parser.parse_args()


def read_prompt_template(prompt_template_file: str) -> str:
    if not prompt_template_file:
        return DEFAULT_PROMPT_TEMPLATE
    with open(prompt_template_file, "r", encoding="utf-8") as f:
        return f.readline().strip()


def finalize_numeric_buffer(buffer, target):
    if buffer:
        try:
            target.append(float("".join(buffer)))
        except ValueError:
            pass
        buffer.clear()


def decode_outputs(output_ids, tokenizer, model):
    vocab_size = model.config.vocab_size
    time_offset = vocab_size + 1
    score_offset = vocab_size + model.config.time_vocab_size + 1

    text_sync_id = vocab_size
    time_sync_id = time_offset
    time_sep_id = time_offset + 1
    score_sync_id = score_offset
    score_sep_id = score_offset + 1

    outputs = {
        "timestamps": [],
        "scores": [],
        "captions": [],
    }

    current_timestamps = []
    current_timestamp = []
    current_scores = []
    current_score = []
    current_caption = []

    for token_id in output_ids[0].tolist():
        if token_id < time_offset:
            if token_id == text_sync_id:
                caption = tokenizer.decode(current_caption, skip_special_tokens=True).strip()
                if caption:
                    outputs["captions"].append(caption)
                current_caption = []
            else:
                current_caption.append(token_id)
            continue

        if token_id < score_offset:
            if token_id == time_sync_id:
                finalize_numeric_buffer(current_timestamp, current_timestamps)
                if current_timestamps:
                    outputs["timestamps"].append(current_timestamps)
                current_timestamps = []
            elif token_id == time_sep_id:
                finalize_numeric_buffer(current_timestamp, current_timestamps)
            else:
                current_timestamp.append(model.get_model().time_tokenizer.decode(token_id - time_offset))
            continue

        if token_id == score_sync_id:
            finalize_numeric_buffer(current_score, current_scores)
            if current_scores:
                outputs["scores"].append(current_scores)
            current_scores = []
        elif token_id == score_sep_id:
            finalize_numeric_buffer(current_score, current_scores)
        else:
            current_score.append(model.get_model().score_tokenizer.decode(token_id - score_offset))

    trailing_caption = tokenizer.decode(current_caption, skip_special_tokens=True).strip()
    if trailing_caption:
        outputs["captions"].append(trailing_caption)

    return outputs


def build_highlights(parsed_outputs):
    count = max(
        len(parsed_outputs["timestamps"]),
        len(parsed_outputs["scores"]),
        len(parsed_outputs["captions"]),
    )
    highlights = []
    for idx in range(count):
        highlights.append(
            {
                "timestamps": parsed_outputs["timestamps"][idx] if idx < len(parsed_outputs["timestamps"]) else [],
                "scores": parsed_outputs["scores"][idx] if idx < len(parsed_outputs["scores"]) else [],
                "caption": parsed_outputs["captions"][idx] if idx < len(parsed_outputs["captions"]) else "",
            }
        )
    return highlights


def main():
    args = parse_args()
    model_path = Path(args.model_path).expanduser().resolve()
    video_path = Path(args.video_path).expanduser().resolve()
    output_json = Path(args.output_json).expanduser().resolve()

    if not model_path.exists():
        raise FileNotFoundError(f"Model path does not exist: {model_path}")
    if not video_path.exists():
        raise FileNotFoundError(f"Video path does not exist: {video_path}")

    output_json.parent.mkdir(parents=True, exist_ok=True)

    if args.device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available, but --device was set to a CUDA device.")

    load_device = "cpu" if args.device == "cpu" else "cuda"
    runtime_device = torch.device(args.device)
    model_name = get_model_name_from_path(str(model_path))
    tokenizer, model, processor, _ = load_pretrained_model(
        str(model_path),
        None,
        model_name,
        device=load_device,
    )
    model = model.to(runtime_device)
    model.eval()

    num_frames = args.num_frames
    if num_frames is None:
        num_frames = getattr(model.config, "num_frames", 8)

    prompt_template = read_prompt_template(args.prompt_template_file)
    question = prompt_template.format(args.query)
    prompt = DEFAULT_MMODAL_TOKEN["VIDEO"] + "\n" + question

    conv = conv_templates["llama_2"].copy()
    conv.append_message(conv.roles[0], prompt)
    conv.append_message(conv.roles[1], None)
    full_prompt = conv.get_prompt() + "<sync>"

    tensor, video_timestamps = process_video(
        str(video_path),
        processor,
        model.config.image_aspect_ratio,
        num_frames=num_frames,
    )

    dtype = torch.float16 if runtime_device.type == "cuda" else torch.float32
    tensor = [tensor.to(dtype=dtype, device=runtime_device, non_blocking=runtime_device.type == "cuda")]
    video_timestamps = [video_timestamps]

    input_ids = tokenizer_MMODAL_token_all(full_prompt, tokenizer, return_tensors="pt").unsqueeze(0).to(runtime_device)
    pad_token_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
    attention_mask = input_ids.ne(pad_token_id).long().to(runtime_device)

    with torch.inference_mode():
        output_ids = model.generate(
            input_ids,
            attention_mask=attention_mask,
            images_or_videos=tensor,
            modal_list=["video"],
            do_sample=False,
            temperature=0.0,
            max_new_tokens=args.max_new_tokens,
            use_cache=True,
            pad_token_id=tokenizer.eos_token_id,
            video_timestamps=video_timestamps,
            heads=[1],
        )

    parsed_outputs = decode_outputs(output_ids, tokenizer, model)
    result = {
        "task": "qvhighlights",
        "model_path": str(model_path),
        "video_path": str(video_path),
        "query": args.query,
        "prompt": question,
        "num_frames": num_frames,
        "sampled_frame_timestamps": video_timestamps[0],
        "timestamps": parsed_outputs["timestamps"],
        "scores": parsed_outputs["scores"],
        "captions": parsed_outputs["captions"],
        "highlights": build_highlights(parsed_outputs),
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps({"output_json": str(output_json)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
