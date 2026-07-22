#!/usr/bin/env python3
from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path


RESPONSES = {
    "s-001": {
        "route": "direct",
        "terminal": "complete",
        "degradation": None,
        "artifacts": [],
    },
    "s-002": {
        "route": "verified",
        "terminal": "complete",
        "degradation": "host-native-verified",
        "artifacts": [
            ".workloop/local/example/goal.json",
            ".workloop/local/example/plan.json",
            ".workloop/local/example/evidence/grading.json",
        ],
    },
    "s-003": {
        "route": "reviewed",
        "terminal": "needs_human",
        "degradation": "labeled-self-review",
        "artifacts": [
            ".workloop/local/example/goal.json",
            ".workloop/local/example/plan.json",
            ".workloop/local/example/review.md",
        ],
    },
    "s-004": {
        "route": "distributed",
        "terminal": "complete",
        "degradation": "durable-serial",
        "artifacts": [
            ".workloop/tracked/example/goal.json",
            ".workloop/tracked/example/plan.json",
            ".workloop/tracked/example/state.json",
            ".workloop/tracked/example/progress.md",
        ],
    },
}


request = json.load(sys.stdin)
response = RESPONSES[request["case_id"]]
artifact_root = Path(request["artifact_root"])
artifacts = []
for relative in response["artifacts"]:
    path = artifact_root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"fixture artifact for {request['case_id']}\n", encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    artifacts.append({"path": relative, "sha256": "sha256:" + digest})
json.dump(
    {
        "schema": "workloop-adapter-response/1",
        "activated": True,
        **response,
        "artifacts": artifacts,
        "trace": {"skill_calls": ["adaptive-workloop"]},
        "usage": {"input_tokens": 0, "output_tokens": 0},
    },
    sys.stdout,
)
