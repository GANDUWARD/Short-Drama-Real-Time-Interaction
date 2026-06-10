#!/usr/bin/env python3
import argparse
import json
import shutil
from pathlib import Path

import torch


if hasattr(torch, "compiler") and not hasattr(torch.compiler, "is_compiling"):
    torch.compiler.is_compiling = lambda: False


def parse_args():
    parser = argparse.ArgumentParser(description="Caption stage-1 highlight clips with a local Qwen2.5-VL model.")
    parser.add_argument("--model-path", required=True, help="Path to the local Qwen2.5-VL model directory.")
    parser.add_argument("--stage1-json", required=True, help="Path to the stage-1 JSON manifest containing clip paths.")
    parser.add_argument("--output-json", required=True, help="Path to the final output JSON file.")
    parser.add_argument("--device", default="cuda", help="Device to run on, usually 'cuda' or 'cpu'.")
    parser.add_argument("--max-new-tokens", type=int, default=96, help="Maximum new tokens for each clip caption.")
    parser.add_argument("--keep-temp-clips", action="store_true", help="Keep temporary stage-1 clip files after captioning.")
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

    stage2_segments = result.get("stage2_segments", [])
    query = result["query"]
    for segment in stage2_segments:
        clip_path = Path(segment.get("clip_path", ""))
        if not clip_path.exists():
            raise FileNotFoundError(f"Clip path does not exist for segment captioning: {clip_path}")
        segment["caption"] = run_qwen_segment_description(
            clip_path,
            query,
            processor,
            model,
            runtime_device,
            args.max_new_tokens,
        )

    result["stage2_backend"] = "qwen2_5_vl"
    result["stage2_model_path"] = str(model_path)
    result.setdefault("settings", {})
    result["settings"]["stage2_backend"] = "qwen2_5_vl"
    result["settings"]["describe_max_new_tokens"] = args.max_new_tokens

    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    if not args.keep_temp_clips:
        for segment in stage2_segments:
            clip_path = Path(segment.get("clip_path", ""))
            if clip_path.exists():
                clip_path.unlink()
        # clean the temporary directory if it is empty after clip deletion
        parent_dirs = {Path(segment.get("clip_path", "")).parent for segment in stage2_segments if segment.get("clip_path")}
        for parent in parent_dirs:
            if parent.exists():
                try:
                    parent.rmdir()
                except OSError:
                    pass

    print(json.dumps({"output_json": str(output_json)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
