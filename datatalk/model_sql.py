from __future__ import annotations

from pathlib import Path

from .prompts import build_text_to_sql_prompt
from .sql_guard import validate_read_only_select


def generate_sql_with_model(question: str, model_dir: Path, max_new_tokens: int = 180) -> str:
    try:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except ImportError as exc:  # pragma: no cover - depends on optional training stack
        raise RuntimeError(
            "Model inference requires torch and transformers. Install requirements-train.txt first."
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_dir)
    device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
    model.to(device)
    model.eval()

    prompt = build_text_to_sql_prompt(question)
    encoded = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024).to(device)
    output = model.generate(
        **encoded,
        max_new_tokens=max_new_tokens,
        num_beams=4,
        do_sample=False,
    )
    sql = tokenizer.decode(output[0], skip_special_tokens=True)
    return validate_read_only_select(sql)
