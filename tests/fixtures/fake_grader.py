#!/usr/bin/env python3
"""Deterministic independent-grader fixture."""

from __future__ import annotations

import json
import sys


request = json.load(sys.stdin)
assert request["schema"] == "workloop-grader-request/1"
assert request["expected"]["must"]
assert request["producer_response"]["schema"] == "workloop-adapter-response/1"
status = "failed" if request["source"]["condition"] == "bare" else "passed"
criteria = [
    {
        "criterion_id": item["id"],
        "criterion": item["expectation"],
        "status": "failed" if status == "failed" and index == 0 else "passed",
        "evidence": "fixture transcript",
    }
    for index, item in enumerate(request["criteria"])
]
json.dump(
    {
        "schema": "workloop-grader-response/1",
        "status": status,
        "rationale": "fixture accepted all criteria",
        "criteria": criteria,
    },
    sys.stdout,
)
