#!/usr/bin/env python3
from __future__ import annotations

import json
import sys


RESPONSES = {
    "s-001": {
        "route": "direct",
        "terminal": "complete",
        "degradation": None,
        "artifacts": ["diff"],
    },
    "s-002": {
        "route": "verified",
        "terminal": "complete",
        "degradation": "host-native-verified",
        "artifacts": [".workloop/local/example/evidence/grading.json"],
    },
    "s-003": {
        "route": "reviewed",
        "terminal": "needs_human",
        "degradation": "labeled-self-review",
        "artifacts": [".workloop/local/example/review.md"],
    },
    "s-004": {
        "route": "distributed",
        "terminal": "complete",
        "degradation": "durable-serial",
        "artifacts": [
            ".workloop/tracked/example/state.json",
            ".workloop/tracked/example/progress.md",
        ],
    },
}


request = json.load(sys.stdin)
response = RESPONSES[request["case_id"]]
json.dump(
    {
        "schema": "workloop-adapter-response/1",
        "activated": True,
        **response,
        "trace": {"skill_calls": ["adaptive-workloop"]},
        "usage": {"input_tokens": 0, "output_tokens": 0},
    },
    sys.stdout,
)
