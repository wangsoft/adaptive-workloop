#!/usr/bin/env python3
"""Invalid grader fixture that asserts success without criterion evidence."""

from __future__ import annotations

import json
import sys


json.load(sys.stdin)
json.dump(
    {
        "schema": "workloop-grader-response/1",
        "status": "passed",
        "rationale": "unsupported aggregate verdict",
        "criteria": [],
    },
    sys.stdout,
)
