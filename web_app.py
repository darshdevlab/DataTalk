#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parent))

from datatalk.config import DB_PATH
from datatalk.data import ensure_db, table_counts
from datatalk.executor import answer_question
from datatalk.model_sql import generate_sql_with_model


EXAMPLES = [
    "Show revenue by region for 2025",
    "Top products by revenue for Q1",
    "Find churn risk tickets for Q4",
    "Show open support tickets by priority for Q1",
    "Employee attrition by department",
    "Show overdue invoices",
]


def render_table(rows: list[dict]) -> str:
    if not rows:
        return "<p class='muted'>No rows returned.</p>"
    columns = list(rows[0].keys())
    header = "".join(f"<th>{html.escape(col)}</th>" for col in columns)
    body_rows = []
    for row in rows[:100]:
        body_rows.append("<tr>" + "".join(f"<td>{html.escape(str(row.get(col, '')))}</td>" for col in columns) + "</tr>")
    return f"<table><thead><tr>{header}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def render_page(question: str = "", result: dict | None = None, error: str = "") -> bytes:
    model_dir = os.environ.get("DATATALK_MODEL_DIR", "").strip()
    mode = "Trained SLM" if model_dir else "Reference router"
    counts = table_counts(DB_PATH)
    example_buttons = "".join(
        f"<button name='question' value='{html.escape(example)}'>{html.escape(example)}</button>"
        for example in EXAMPLES
    )
    result_html = ""
    if error:
        result_html = f"<section class='panel error'><h2>Error</h2><p>{html.escape(error)}</p></section>"
    elif result:
        result_html = f"""
        <section class="panel">
          <div class="result-head">
            <div>
              <h2>{html.escape(result["answer"])}</h2>
              <p class="muted">Route: {html.escape(result["route"])} | Confidence: {result["confidence"]:.2f} | Latency: {result["latency_ms"]:.1f} ms</p>
            </div>
          </div>
          <h3>Executed SQL</h3>
          <pre>{html.escape(result["sql"])}</pre>
          <h3>Source Rows</h3>
          {render_table(result["rows"])}
        </section>
        """

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DataTalk</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #172026;
      --muted: #5c6870;
      --line: #d8dee4;
      --surface: #ffffff;
      --band: #f6f7f9;
      --accent: #0f766e;
      --accent-ink: #ffffff;
      --warn: #9f1239;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--band);
    }}
    header {{
      border-bottom: 1px solid var(--line);
      background: var(--surface);
    }}
    .wrap {{
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
    }}
    .topbar {{
      min-height: 72px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }}
    h1 {{ margin: 0; font-size: 26px; font-weight: 760; }}
    h2 {{ margin: 0 0 8px; font-size: 20px; }}
    h3 {{ margin: 20px 0 8px; font-size: 14px; text-transform: uppercase; color: var(--muted); }}
    .badge {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 7px 10px;
      font-size: 13px;
      color: var(--muted);
      background: #fbfcfd;
      white-space: nowrap;
    }}
    main {{ padding: 22px 0 36px; }}
    .grid {{
      display: grid;
      grid-template-columns: 330px 1fr;
      gap: 18px;
      align-items: start;
    }}
    .panel {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .querybox textarea {{
      width: 100%;
      min-height: 120px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
      font: inherit;
      color: var(--ink);
      background: #fff;
    }}
    .primary {{
      width: 100%;
      margin-top: 10px;
      border: 0;
      border-radius: 6px;
      padding: 11px 12px;
      background: var(--accent);
      color: var(--accent-ink);
      font-weight: 700;
      cursor: pointer;
    }}
    .examples {{
      display: grid;
      gap: 8px;
      margin-top: 12px;
    }}
    .examples button {{
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      padding: 9px 10px;
      text-align: left;
      cursor: pointer;
    }}
    .stats {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 12px;
    }}
    .stat {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: #fbfcfd;
    }}
    .stat strong {{ display: block; font-size: 18px; }}
    .muted {{ color: var(--muted); font-size: 13px; margin: 0; }}
    pre {{
      overflow: auto;
      white-space: pre-wrap;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
      background: #f8fafc;
      font-size: 13px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 8px 9px;
      text-align: left;
      vertical-align: top;
    }}
    th {{ background: #f8fafc; font-weight: 700; }}
    .error {{ border-color: #fecdd3; color: var(--warn); }}
    @media (max-width: 840px) {{
      .grid {{ grid-template-columns: 1fr; }}
      .topbar {{ align-items: flex-start; flex-direction: column; padding: 14px 0; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="wrap topbar">
      <div>
        <h1>DataTalk</h1>
        <p class="muted">Natural-language questions over a synthetic company database with executed SQL evidence.</p>
      </div>
      <span class="badge">{html.escape(mode)}</span>
    </div>
  </header>
  <main class="wrap grid">
    <aside class="panel querybox">
      <form method="post" action="/query">
        <textarea name="question" autofocus>{html.escape(question)}</textarea>
        <button class="primary" type="submit">Run Query</button>
      </form>
      <h3>Examples</h3>
      <form class="examples" method="post" action="/query">{example_buttons}</form>
      <h3>Database</h3>
      <div class="stats">
        {''.join(f"<div class='stat'><strong>{count}</strong><span class='muted'>{html.escape(name)}</span></div>" for name, count in counts.items())}
      </div>
    </aside>
    <section>
      {result_html or "<section class='panel'><h2>Ask a company-data question.</h2><p class='muted'>Answers include the SQL that was executed and the source rows returned from SQLite.</p></section>"}
    </section>
  </main>
</body>
</html>"""
    return html_doc.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json({"ok": True})
            return
        self._send_html(render_page())

    def do_POST(self) -> None:
        if self.path != "/query":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        question = parse_qs(body).get("question", [""])[0].strip()
        result = None
        error = ""
        if question:
            try:
                sql = None
                model_dir = os.environ.get("DATATALK_MODEL_DIR", "").strip()
                if model_dir:
                    sql = generate_sql_with_model(question, Path(model_dir))
                response = answer_question(question, DB_PATH, sql=sql)
                result = {
                    "answer": response.answer,
                    "route": response.route,
                    "confidence": response.confidence,
                    "latency_ms": response.latency_ms,
                    "sql": response.sql,
                    "rows": response.rows,
                }
            except Exception as exc:  # pragma: no cover - UI boundary
                error = str(exc)
        self._send_html(render_page(question=question, result=result, error=error))

    def log_message(self, format: str, *args) -> None:
        return

    def _send_html(self, payload: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the DataTalk local web UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    ensure_db(DB_PATH)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"DataTalk UI: http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
