#!/usr/bin/env python3
from __future__ import annotations

import argparse
import inspect
import json
import random
import re
import time
from pathlib import Path

from datatalk.config import MODELS_DIR, REPORTS_DIR, TRAINING_DIR, ensure_artifact_dirs


def load_jsonl(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
            if limit and len(records) >= limit:
                break
    return records


def normalize_sql_for_metric(sql: str) -> str:
    cleaned = " ".join(str(sql).strip().split()).lower()
    cleaned = re.sub(r"\s*([(),=<>+*/-])\s*", r"\1", cleaned)
    return cleaned.rstrip(";")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune a small seq2seq model for DataTalk text-to-SQL.")
    parser.add_argument("--train-file", default=str(TRAINING_DIR / "mixed_text_to_sql_train.jsonl"))
    parser.add_argument("--validation-file", default=str(TRAINING_DIR / "mixed_text_to_sql_validation.jsonl"))
    parser.add_argument("--model-name", default="google/flan-t5-small")
    parser.add_argument("--output-dir", default=str(MODELS_DIR / "flan-t5-small-datatalk"))
    parser.add_argument("--epochs", type=float, default=3)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=5e-5)
    parser.add_argument("--max-input-length", type=int, default=768)
    parser.add_argument("--max-output-length", type=int, default=220)
    parser.add_argument("--limit", type=int, default=0, help="Optional record limit for smoke training.")
    parser.add_argument("--eval-limit", type=int, default=0, help="Optional validation record limit for quicker runs.")
    parser.add_argument("--gradient-accumulation-steps", type=int, default=1)
    parser.add_argument("--eval-strategy", choices=["epoch", "steps"], default="epoch")
    parser.add_argument("--save-strategy", choices=["epoch", "steps"], default="epoch")
    parser.add_argument("--eval-steps", type=int, default=0)
    parser.add_argument("--save-steps", type=int, default=0)
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args()

    try:
        import torch
        from datasets import Dataset
        from transformers import (
            AutoModelForSeq2SeqLM,
            AutoTokenizer,
            DataCollatorForSeq2Seq,
            Seq2SeqTrainer,
            Seq2SeqTrainingArguments,
        )
    except ImportError as exc:
        raise SystemExit(
            "Missing training dependencies. Install with: pip install -r requirements-train.txt"
        ) from exc

    ensure_artifact_dirs()
    device_hint = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    print(json.dumps({"event": "device_check", "device_hint": device_hint, "mps_available": torch.backends.mps.is_available()}))

    train_file = Path(args.train_file)
    records = load_jsonl(train_file, limit=args.limit or None)
    if len(records) < 10:
        raise SystemExit(f"Need at least 10 training records, found {len(records)} in {train_file}")

    validation_file = Path(args.validation_file)
    validation_records = load_jsonl(validation_file, limit=args.eval_limit or None)
    if len(validation_records) < 5:
        raise SystemExit(f"Need at least 5 validation records, found {len(validation_records)} in {validation_file}")

    random.Random(args.seed).shuffle(records)
    train_records = records
    eval_records = validation_records

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model_name)

    def tokenize(batch: dict[str, list[str]]) -> dict:
        model_inputs = tokenizer(
            batch["input"],
            max_length=args.max_input_length,
            truncation=True,
        )
        labels = tokenizer(
            text_target=batch["output"],
            max_length=args.max_output_length,
            truncation=True,
        )
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    train_dataset = Dataset.from_list(train_records).map(tokenize, batched=True, remove_columns=list(train_records[0].keys()))
    eval_dataset = Dataset.from_list(eval_records).map(tokenize, batched=True, remove_columns=list(eval_records[0].keys()))

    output_dir = Path(args.output_dir)
    signature = inspect.signature(Seq2SeqTrainingArguments)
    eval_key = "eval_strategy" if "eval_strategy" in signature.parameters else "evaluation_strategy"
    training_kwargs = {
        "output_dir": str(output_dir),
        "learning_rate": args.lr,
        "per_device_train_batch_size": args.batch_size,
        "per_device_eval_batch_size": args.batch_size,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "num_train_epochs": args.epochs,
        "predict_with_generate": True,
        eval_key: args.eval_strategy,
        "save_strategy": args.save_strategy,
        "logging_steps": 20,
        "save_total_limit": 2,
        "report_to": [],
        "seed": args.seed,
        "load_best_model_at_end": True,
        "metric_for_best_model": "exact_match",
        "greater_is_better": True,
        "generation_max_length": args.max_output_length,
        "dataloader_pin_memory": False,
    }
    if args.eval_strategy == "steps" and args.eval_steps > 0:
        training_kwargs["eval_steps"] = args.eval_steps
    if args.save_strategy == "steps" and args.save_steps > 0:
        training_kwargs["save_steps"] = args.save_steps
    training_args = Seq2SeqTrainingArguments(**training_kwargs)

    def compute_metrics(eval_preds) -> dict[str, float]:
        predictions, labels = eval_preds
        if isinstance(predictions, tuple):
            predictions = predictions[0]
        try:
            import numpy as np

            predictions = np.asarray(predictions)
            if predictions.ndim == 3:
                predictions = predictions.argmax(axis=-1)
            pad_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else 0
            vocab_size = len(tokenizer)
            predictions = np.where((predictions < 0) | (predictions >= vocab_size), pad_id, predictions)
            predictions = predictions.astype("int64")
            labels = np.asarray(labels)
            labels = np.where(labels == -100, pad_id, labels).astype("int64")
        except Exception:
            pass
        decoded_predictions = tokenizer.batch_decode(predictions, skip_special_tokens=True)
        decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)
        exact = [
            normalize_sql_for_metric(prediction) == normalize_sql_for_metric(label)
            for prediction, label in zip(decoded_predictions, decoded_labels)
        ]
        return {"exact_match": sum(exact) / max(1, len(exact))}

    trainer_signature = inspect.signature(Seq2SeqTrainer)
    tokenizer_arg = "processing_class" if "processing_class" in trainer_signature.parameters else "tokenizer"
    trainer_kwargs = {
        "model": model,
        "args": training_args,
        "train_dataset": train_dataset,
        "eval_dataset": eval_dataset,
        "data_collator": DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model),
        "compute_metrics": compute_metrics,
        tokenizer_arg: tokenizer,
    }
    trainer = Seq2SeqTrainer(**trainer_kwargs)
    print(json.dumps({"event": "trainer_ready", "device": str(trainer.args.device), "train_records": len(train_records), "eval_records": len(eval_records)}))
    started_at = time.time()
    train_result = trainer.train()
    metrics = trainer.evaluate()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    metadata = {
        "base_model": args.model_name,
        "train_file": str(train_file),
        "validation_file": str(validation_file),
        "train_records": len(train_records),
        "eval_records": len(eval_records),
        "metrics": metrics,
        "train_metrics": train_result.metrics,
        "training_seconds": time.time() - started_at,
        "device": str(trainer.args.device),
        "purpose": "DataTalk company-schema text-to-SQL specialization",
    }
    (output_dir / "datatalk_model_card.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "slm_training_report.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps({"output_dir": str(output_dir), **metadata}, indent=2))


if __name__ == "__main__":
    main()
