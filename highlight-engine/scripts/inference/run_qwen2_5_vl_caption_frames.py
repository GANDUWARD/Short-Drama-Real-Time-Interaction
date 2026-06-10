#!/usr/bin/env python3
import argparse
import json
import shutil
import tempfile
from pathlib import Path

import av
import torch


if hasattr(torch, "compiler") and not hasattr(torch.compiler, "is_compiling"):
    torch.compiler.is_compiling = lambda: False


def parse_args():
    parser = argparse.ArgumentParser(description="Caption every frame of stage-1 highlight clips with a local Qwen2.5-VL model.")
    parser.add_argument("--model-path", required=True, help="Path to the local Qwen2.5-VL model directory.")
    parser.add_argument("--stage1-json", required=True, help="Path to the stage-1 JSON manifest containing clip paths.")
    parser.add_argument("--output-json", required=True, help="Path to the final output JSON file.")
    parser.add_argument("--device", default="cuda", help="Device to run on, usually 'cuda' or 'cpu'.")
    parser.add_argument("--max-new-tokens", type=int, default=64, help="Maximum new tokens for each frame caption.")
    parser.add_argument("--frame-stride", type=int, default=1, help="Caption every Nth frame. 1 means every frame.")
    parser.add_argument("--keep-temp-files", action="store_true", help="Keep temporary frame images and clip files.")
    return parser.parse_args()


def clean_generated_text(text):
    text = text.strip()
    text = text.replace("</s>", "").strip()
    return " ".join(text.split())


def load_qwen_bundle(model_path, device):
    from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

    runtime_device = torch.device(device)
    torch_dtype = torch.float32
    processor = AutoProcessor.from_pretrained(str(model_path), trust_remote_code=True)
    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        str(model_path),
        torch_dtype=torch_dtype,
        trust_remote_code=True,
    )
    model = model.to(runtime_device)
    model.eval()
    return processor, model, runtime_device


def caption_image(image_path, query, processor, model, runtime_device, max_new_tokens):
    prompt = (
        f"This image is one frame from a highlight candidate for the query: {query}\n"
        "Describe in one short sentence what is happening in this frame and why it matches the query. "
        "Only output the description."
    )
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "path": str(image_path)},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
    ).to(runtime_device)

    with torch.inference_mode():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            use_cache=True,
        )

    generated_ids = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, output_ids)]
    output_text = processor.batch_decode(
        generated_ids,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )[0]
    return clean_generated_text(output_text)


def extract_frames_with_timestamps(video_path, output_dir, frame_stride):
    container = av.open(str(video_path))
    stream = container.streams.video[0]
    frames = []
    for frame_index, frame in enumerate(container.decode(stream)):
        if frame_stride > 1 and frame_index % frame_stride != 0:
            continue
        timestamp = float(frame.time) if frame.time is not None else None
        if timestamp is None:
            if frame.pts is not None and stream.time_base is not None:
                timestamp = float(frame.pts * stream.time_base)
            elif stream.average_rate is not None:
                timestamp = frame_index / float(stream.average_rate)
            else:
                timestamp = float(frame_index)
        image_path = output_dir / f"frame_{frame_index:06d}.jpg"
        frame.to_image().save(image_path, quality=95)
        frames.append(
            {
                "frame_index": frame_index,
                "timestamp": round(timestamp, 3),
                "image_path": str(image_path),
            }
        )
    container.close()
    return frames


def main():
    args = parse_args()
    model_path = Path(args.model_path).expanduser().resolve()
    stage1_json = Path(args.stage1_json).expanduser().resolve()
    output_json = Path(args.output_json).expanduser().resolve()

    if not model_path.exists():
        raise FileNotFoundError(f"Model path does not exist: {model_path}")
    if not stage1_json.exists():
        raise FileNotFoundError(f"Stage-1 JSON does not exist: {stage1_json}")
    if args.device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available, but --device was set to a CUDA device.")

    with open(stage1_json, "r", encoding="utf-8") as f:
        result = json.load(f)

    processor, model, runtime_device = load_qwen_bundle(model_path, args.device)
    query = result["query"]
    temp_root = Path(tempfile.mkdtemp(prefix="qwen_frame_caption_", dir=str(output_json.parent)))

    try:
        stage2_segments = result.get("stage2_segments", [])
        for segment_idx, segment in enumerate(stage2_segments, start=1):
            clip_path = Path(segment.get("clip_path", ""))
            if not clip_path.exists():
                raise FileNotFoundError(f"Clip path does not exist for segment frame captioning: {clip_path}")

            frame_dir = temp_root / f"segment_{segment_idx:02d}"
            frame_dir.mkdir(parents=True, exist_ok=True)
            frames = extract_frames_with_timestamps(clip_path, frame_dir, args.frame_stride)
            frame_captions = []
            for frame_info in frames:
                caption = caption_image(
                    frame_info["image_path"],
                    query,
                    processor,
                    model,
                    runtime_device,
                    args.max_new_tokens,
                )
                frame_captions.append(
                    {
                        "frame_index": frame_info["frame_index"],
                        "timestamp": frame_info["timestamp"],
                        "caption": caption,
                        **({"image_path": frame_info["image_path"]} if args.keep_temp_files else {}),
                    }
                )
            segment["frame_captions"] = frame_captions
            if not args.keep_temp_files:
                segment.pop("clip_path", None)

        result["task"] = "qvhighlights_two_stage_framewise"
        result["stage2_backend"] = "qwen2_5_vl_framewise"
        result["stage2_model_path"] = str(model_path)
        result.setdefault("settings", {})
        result["settings"]["stage2_backend"] = "qwen2_5_vl_framewise"
        result["settings"]["frame_stride"] = args.frame_stride
        result["settings"]["describe_max_new_tokens"] = args.max_new_tokens

        output_json.parent.mkdir(parents=True, exist_ok=True)
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    finally:
        if not args.keep_temp_files:
            shutil.rmtree(temp_root, ignore_errors=True)

    print(json.dumps({"output_json": str(output_json)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
