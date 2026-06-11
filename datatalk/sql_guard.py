from __future__ import annotations

import re


FORBIDDEN_SQL = {
    "alter",
    "attach",
    "create",
    "delete",
    "detach",
    "drop",
    "insert",
    "pragma",
    "replace",
    "truncate",
    "update",
    "vacuum",
}


class UnsafeSQL(ValueError):
    """Raised when generated SQL is not allowed for the demo executor."""


def normalize_sql(sql: str) -> str:
    cleaned = " ".join(sql.strip().split())
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()
    return cleaned


def validate_read_only_select(sql: str) -> str:
    cleaned = normalize_sql(sql)
    if not cleaned:
        raise UnsafeSQL("SQL is empty.")
    if ";" in cleaned:
        raise UnsafeSQL("Only one SQL statement is allowed.")
    if not cleaned.lower().startswith("select "):
        raise UnsafeSQL("Only SELECT statements are allowed.")
    tokens = set(re.findall(r"[a-zA-Z_]+", cleaned.lower()))
    blocked = sorted(tokens.intersection(FORBIDDEN_SQL))
    if blocked:
        raise UnsafeSQL(f"Forbidden SQL keyword(s): {', '.join(blocked)}.")
    return cleaned


def ensure_limit(sql: str, limit: int = 200) -> str:
    cleaned = validate_read_only_select(sql)
    lowered = cleaned.lower()
    if re.search(r"\blimit\s+\d+\b", lowered):
        return cleaned
    return f"{cleaned} LIMIT {int(limit)}"
