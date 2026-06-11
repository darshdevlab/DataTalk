from __future__ import annotations

from .schema import schema_context


def build_text_to_sql_prompt(question: str) -> str:
    return (
        "You are DataTalk-SQL, a small model specialized for this company database. "
        "Return exactly one safe SQLite SELECT query. Do not explain.\n\n"
        f"{schema_context()}\n\n"
        f"Question: {question.strip()}\n"
        "SQL:"
    )
