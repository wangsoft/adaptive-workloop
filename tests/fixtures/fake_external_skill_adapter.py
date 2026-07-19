#!/usr/bin/env python3
from __future__ import annotations

import json
import sys


json.load(sys.stdin)
json.dump(
    {
        "schema": "workloop-adapter-response/1",
        "activated": True,
        "route": "direct",
        "terminal": "complete",
        "degradation": None,
        "artifacts": [],
        "trace": {"skill_calls": ["adaptive-workloop", "gstack"]},
        "usage": {"input_tokens": 0, "output_tokens": 0},
    },
    sys.stdout,
)
