---
title: DataTalk
emoji: 📊
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# DataTalk

DataTalk is a demo API for natural-language querying over a synthetic company
database. The deployed Space uses the reliable intent/slot compiler path:

1. classify the supported query intent,
2. compile a read-only SQL template,
3. execute SQL against a demo SQLite database,
4. return SQL, rows, answer text, route, confidence, and latency.

The experimental local T5 fine-tuned model is not required for this public demo.
