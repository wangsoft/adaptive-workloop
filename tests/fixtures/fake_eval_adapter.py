#!/usr/bin/env python3
from __future__ import annotations

import json
import sys


request = json.load(sys.stdin)
prompt = request["prompt"].lower()
activated = "resume the workloop" in prompt
json.dump(
    {
        "schema": "workloop-adapter-response/1",
        "activated": activated,
        "route": None,
        "transcript": "fixture response",
        "usage": {"input_tokens": 0, "output_tokens": 0},
    },
    sys.stdout,
)
