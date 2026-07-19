#!/usr/bin/env python3
"""Fail exactly once, then behave like the deterministic producer fixture."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


marker = Path(os.environ["MATRIX_FAIL_MARKER"])
if not marker.exists():
    marker.write_text("failed\n", encoding="utf-8")
    raise SystemExit(1)

request = json.load(sys.stdin)
json.dump(
    {
        "schema": "workloop-adapter-response/1",
        "activated": request["condition"] != "bare",
        "route": "verified" if request["condition"] != "bare" else None,
        "transcript": "fixture response after recovery",
        "usage": {"input_tokens": 0, "output_tokens": 0},
    },
    sys.stdout,
)
