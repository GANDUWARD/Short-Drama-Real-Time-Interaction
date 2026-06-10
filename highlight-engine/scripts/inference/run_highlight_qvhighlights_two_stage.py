#!/usr/bin/env python3
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import torch


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from highlight.constants import DEFAULT_MMODAL_TOKEN, MMODAL_TOKEN_INDEX
from highlight.conversation import SeparatorStyle, conv_templates
from highlight.mm_utils import (
    KeywordsStoppingCriteria,
    get_model_name_from_path,
    process_video,
    tokenizer_MMODAL_token,
    tokenizer_MMODAL_token_all,
)
from highlight.model.builder import load_pretrained_model


DETECTION_PROMPT_TEMPLATE = (
    "Please find the highlight contents in the video described by a sentence query, "
    "determining the highlight timestamps and its saliency score on a scale from 1 to 5. "
    "Now I will give you the sentence query: '{}'. "
    "Please return the query-based highlight timestamps and salient scores."
)

DESCRIPTION_PROMPT_TEMPLATE = (
    "This clip is a highlight candidate for the query '{}'. "
    "Describe in one short sentence what happens in this clip and why it matches the query. "
    "Only output the description."
)


def parse_args():
    parser = argparse.ArgumentParser(description="Two-stage highlight inference: detect highlights, then caption each merged segment.")
    parser.add_argument("--model-path", required=True, help="Path to the local highlight model directory.")
    parser.add_argument("--stage2-model-path", default="", help="Optional stage-2 caption model path. Defaults to --model-path.")
    parser.add_argument("--stage2-backend", choices=["highlight", "qwen2_5_vl", "none"], default="highlight", help="Caption backend used in stage 2.")
    parser.add_argument("--video-path", required=True, help="Path to the input video.")
    parser.add_argument("--query", required=True, help="Sentence query for QVHighlights-style highlight detection.")
    parser.add_argument("--output-json", required=True, help="Path to the output JSON file.")
    parser.add_argument("--device", default="cuda", help="Device to run on, usually 'cuda' or 'cpu'.")
    parser.add_argument("--detect-num-frames", type=int, default=128, help="Frame count used in stage-1 highlight detection.")
    parser.add_argument("--describe-num-frames", type=int, default=64, help="Frame count used when captioning each detected segment.")
    parser.add_argument("--detect-max-new-tokens", type=int, default=512, help="Max new tokens for stage-1 detection.")
    parser.add_argument("--describe-max-new-tokens", type=int, default=96, help="Max new tokens for stage-2 caption generation.")
    parser.add_argument("--min-score", type=float, default=3.0, help="Minimum score required for a highlight point to be kept.")
    parser.add_argument("--merge-gap", type=float, default=0.75, help="Max gap between adjacent highlight points to merge into one segment.")
    parser.add_argument("--segment-padding", type=float, default=1.0, help="Seconds of padding added to both sides of a merged segment.")
    parser.add_argument("--min-segment-seconds", type=float, default=2.0, help="Minimum duration of each merged segment.")
    parser.add_argument("--max-segments", type=int, default=5, help="Maximum number of merged segments to caption.")
    parser.add_argument("--keep-temp-clips", action="store_true", help="Keep temporary clipped segment files for inspection.")
    return parser.parse_args()


def finalize_numeric_buffer(buffer, target):
    if buffer:
        try:
            target.append(float("".join(buffer)))
        except ValueError:
            pass
        buffer.clear()


def decode_structured_outputs(output_ids, tokenizer, model):
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


def load_model_bundle(model_path, device):
    load_device = "cpu" if device == "cpu" else "cuda"
    runtime_device = torch.device(device)
    model_name = get_model_name_from_path(str(model_path))
    tokenizer, model, processor, _ = load_pretrained_model(
        str(model_path),
        None,
        model_name,
        device=load_device,
    )
    model = model.to(runtime_device)
    model.eval()
    return tokenizer, model, processor, runtime_device


def load_qwen_bundle(model_path, device):
    try:
        from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
    except ImportError as exc:
        raise RuntimeError(
            "Qwen2.5-VL stage-2 captioning requires a newer Transformers build that provides "
            "`Qwen2_5_VLForConditionalGeneration` and `AutoProcessor` support for `qwen2_5_vl`."
        ) from exc

    runtime_device = torch.device(device)
    torch_dtype = torch.bfloat16 if runtime_device.type == "cuda" else torch.float32
    processor = AutoProcessor.from_pretrained(str(model_path), trust_remote_code=True)
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        str(model_path),
        torch_dtype=torch_dtype,
        trust_remote_code=True,
    )
    model = model.to(runtime_device)
    model.eval()
    return processor, model, runtime_device


def preprocess_video(video_path, processor, model, runtime_device, num_frames):
    tensor, video_timestamps = process_video(
        str(video_path),
        processor,
        model.config.image_aspect_ratio,
        num_frames=num_frames,
    )
    dtype = torch.float16 if runtime_device.type == "cuda" else torch.float32
    tensor = [tensor.to(dtype=dtype, device=runtime_device, non_blocking=runtime_device.type == "cuda")]
    return tensor, [video_timestamps]


def run_highlight_detection(video_path, query, tokenizer, model, processor, runtime_device, num_frames, max_new_tokens):
    question = DETECTION_PROMPT_TEMPLATE.format(query)
    prompt = DEFAULT_MMODAL_TOKEN["VIDEO"] + "\n" + question

    conv = conv_templates["llama_2"].copy()
    conv.append_message(conv.roles[0], prompt)
    conv.append_message(conv.roles[1], None)
    full_prompt = conv.get_prompt() + "<sync>"

    tensor, video_timestamps = preprocess_video(video_path, processor, model, runtime_device, num_frames)
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
            max_new_tokens=max_new_tokens,
            use_cache=True,
            pad_token_id=tokenizer.eos_token_id,
            video_timestamps=video_timestamps,
            heads=[1],
        )

    parsed_outputs = decode_structured_outputs(output_ids, tokenizer, model)
    return {
        "prompt": question,
        "num_frames": num_frames,
        "sampled_frame_timestamps": video_timestamps[0],
        "timestamps": parsed_outputs["timestamps"],
        "scores": parsed_outputs["scores"],
        "captions": parsed_outputs["captions"],
    }


def flatten_scored_points(detection_result):
    points = []
    timestamps = detection_result["timestamps"]
    scores = detection_result["scores"]
    for idx, timestamp_values in enumerate(timestamps):
        if not timestamp_values:
            continue
        time_value = timestamp_values[0]
        score_values = scores[idx] if idx < len(scores) else []
        score_value = score_values[0] if score_values else None
        points.append({"time": float(time_value), "score": score_value})
    return points


def merge_highlight_points(points, min_score, merge_gap, padding, min_segment_seconds, max_segments):
    kept_points = [point for point in points if point["score"] is not None and point["score"] >= min_score]
    if not kept_points:
        return []

    kept_points.sort(key=lambda item: item["time"])
    groups = [[kept_points[0]]]
    for point in kept_points[1:]:
        if point["time"] - groups[-1][-1]["time"] <= merge_gap:
            groups[-1].append(point)
        else:
            groups.append([point])

    segments = []
    for group in groups:
        raw_start = group[0]["time"]
        raw_end = group[-1]["time"]
        start = max(0.0, raw_start - padding)
        end = raw_end + padding
        if end - start < min_segment_seconds:
            center = (raw_start + raw_end) / 2.0
            half = min_segment_seconds / 2.0
            start = max(0.0, center - half)
            end = center + half
        segment = {
            "start": round(start, 2),
            "end": round(end, 2),
            "raw_start": round(raw_start, 2),
            "raw_end": round(raw_end, 2),
            "num_points": len(group),
            "min_score": round(min(point["score"] for point in group), 2),
            "max_score": round(max(point["score"] for point in group), 2),
            "avg_score": round(sum(point["score"] for point in group) / len(group), 2),
            "points": [{"time": round(point["time"], 2), "score": round(point["score"], 2)} for point in group],
        }
        segments.append(segment)

    segments.sort(key=lambda item: (-item["max_score"], -item["avg_score"], item["start"]))
    segments = segments[:max_segments]
    segments.sort(key=lambda item: item["start"])
    return segments


def clip_video_segment(video_path, segment, output_dir, segment_idx):
    clip_path = output_dir / f"segment_{segment_idx:02d}_{segment['start']:.2f}_{segment['end']:.2f}.mp4"
    command = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-ss",
        str(segment["start"]),
        "-to",
        str(segment["end"]),
        "-i",
        str(video_path),
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "18",
        "-an",
        str(clip_path),
    ]
    subprocess.run(command, check=True)
    return clip_path


def clean_generated_text(text):
    text = text.strip()
    text = text.replace("</s>", "").strip()
    if "[/INST]" in text:
        text = text.split("[/INST]", 1)[-1].strip()
    if "<s>" in text:
        text = text.split("<s>")[-1].strip()
    return " ".join(text.split())


def decode_text_only(output_ids, tokenizer, prompt_length):
    generated_ids = output_ids[0, prompt_length:]
    generated_ids = generated_ids[generated_ids < tokenizer.vocab_size]
    if generated_ids.numel() == 0:
        return ""
    return tokenizer.decode(generated_ids, skip_special_tokens=True)


def run_segment_description(video_path, query, tokenizer, model, processor, runtime_device, num_frames, max_new_tokens):
    question = DESCRIPTION_PROMPT_TEMPLATE.format(query)
    prompt = DEFAULT_MMODAL_TOKEN["VIDEO"] + "\n" + question

    conv = conv_templates["llama_2"].copy()
    conv.append_message(conv.roles[0], prompt)
    conv.append_message(conv.roles[1], None)
    full_prompt = conv.get_prompt()

    tensor, video_timestamps = preprocess_video(video_path, processor, model, runtime_device, num_frames)
    input_ids = tokenizer_MMODAL_token(
        full_prompt,
        tokenizer,
        MMODAL_TOKEN_INDEX["VIDEO"],
        return_tensors="pt",
    ).unsqueeze(0).to(runtime_device)
    pad_token_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
    attention_mask = input_ids.ne(pad_token_id).long().to(runtime_device)
    stop_str = conv.sep if conv.sep_style in [SeparatorStyle.SINGLE, SeparatorStyle.QWEN] else conv.sep2
    stopping_criteria = KeywordsStoppingCriteria([stop_str], tokenizer, input_ids)

    with torch.inference_mode():
        output_ids = model.generate(
            input_ids,
            attention_mask=attention_mask,
            images_or_videos=tensor,
            modal_list=["video"],
            do_sample=False,
            temperature=0.0,
            max_new_tokens=max_new_tokens,
            use_cache=True,
            stopping_criteria=[stopping_criteria],
            pad_token_id=tokenizer.eos_token_id,
            video_timestamps=video_timestamps,
        )

    decoded_text = decode_text_only(output_ids, tokenizer, input_ids.shape[1])
    return clean_generated_text(decoded_text)


def run_qwen_segment_description(video_path, query, processor, model, runtime_device, max_new_tokens):
    prompt = (
        f"This video clip is a highlight candidate for the query: {query}\n"
        "Describe in one short sentence what happens in this clip and why it matches the query. "
        "Only output the description."
    )
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "video", "path": str(video_path)},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    inputs = processor.apply_chat_template(
        messages,
        fps=1,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
    ).to(runtime_device)

    with torch.inference_mode():
        output_ids = model.generate(**inputs, max_new_tokens=max_new_tokens)

    generated_ids = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, output_ids)]
    output_text = processor.batch_decode(
        generated_ids,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )[0]
    return clean_generated_text(output_text)


def main():
    args = parse_args()
    model_path = Path(args.model_path).expanduser().resolve()
    stage2_model_path = Path(args.stage2_model_path).expanduser().resolve() if args.stage2_model_path else model_path
    video_path = Path(args.video_path).expanduser().resolve()
    output_json = Path(args.output_json).expanduser().resolve()

    if not model_path.exists():
        raise FileNotFoundError(f"Model path does not exist: {model_path}")
    if not stage2_model_path.exists():
        raise FileNotFoundError(f"Stage-2 model path does not exist: {stage2_model_path}")
    if not video_path.exists():
        raise FileNotFoundError(f"Video path does not exist: {video_path}")
    if args.device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available, but --device was set to a CUDA device.")
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg was not found in PATH.")

    output_json.parent.mkdir(parents=True, exist_ok=True)
    tokenizer, model, processor, runtime_device = load_model_bundle(model_path, args.device)
    stage2_bundle = None
    if args.stage2_backend == "highlight":
        stage2_bundle = (tokenizer, model, processor, runtime_device)
    elif args.stage2_backend == "qwen2_5_vl":
        stage2_bundle = load_qwen_bundle(stage2_model_path, args.device)
    else:
        stage2_bundle = None

    detection_result = run_highlight_detection(
        video_path,
        args.query,
        tokenizer,
        model,
        processor,
        runtime_device,
        args.detect_num_frames,
        args.detect_max_new_tokens,
    )

    points = flatten_scored_points(detection_result)
    merged_segments = merge_highlight_points(
        points,
        args.min_score,
        args.merge_gap,
        args.segment_padding,
        args.min_segment_seconds,
        args.max_segments,
    )

    temp_dir = Path(tempfile.mkdtemp(prefix="highlight_qv_segments_", dir=str(output_json.parent)))
    described_segments = []
    try:
        for idx, segment in enumerate(merged_segments, start=1):
            clip_path = clip_video_segment(video_path, segment, temp_dir, idx)
            if args.stage2_backend == "highlight":
                caption = run_segment_description(
                    clip_path,
                    args.query,
                    stage2_bundle[0],
                    stage2_bundle[1],
                    stage2_bundle[2],
                    stage2_bundle[3],
                    args.describe_num_frames,
                    args.describe_max_new_tokens,
                )
            elif args.stage2_backend == "qwen2_5_vl":
                caption = run_qwen_segment_description(
                    clip_path,
                    args.query,
                    stage2_bundle[0],
                    stage2_bundle[1],
                    stage2_bundle[2],
                    args.describe_max_new_tokens,
                )
            else:
                caption = ""
            described_segment = dict(segment)
            described_segment["caption"] = caption
            if args.keep_temp_clips or args.stage2_backend == "none":
                described_segment["clip_path"] = str(clip_path)
            described_segments.append(described_segment)
    finally:
        if not args.keep_temp_clips:
            shutil.rmtree(temp_dir, ignore_errors=True)

    result = {
        "task": "qvhighlights_two_stage",
        "model_path": str(model_path),
        "stage2_model_path": str(stage2_model_path),
        "stage2_backend": args.stage2_backend,
        "video_path": str(video_path),
        "query": args.query,
        "stage1_detection": detection_result,
        "stage1_points": points,
        "stage2_segments": described_segments,
        "settings": {
            "detect_num_frames": args.detect_num_frames,
            "describe_num_frames": args.describe_num_frames,
            "detect_max_new_tokens": args.detect_max_new_tokens,
            "describe_max_new_tokens": args.describe_max_new_tokens,
            "stage2_backend": args.stage2_backend,
            "min_score": args.min_score,
            "merge_gap": args.merge_gap,
            "segment_padding": args.segment_padding,
            "min_segment_seconds": args.min_segment_seconds,
            "max_segments": args.max_segments,
            "keep_temp_clips": args.keep_temp_clips,
        },
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps({"output_json": str(output_json)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
