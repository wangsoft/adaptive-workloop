#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys


json.load(sys.stdin)
json.dump(
    {
        "schema": "workloop-adapter-response/1",
        "activated": False,
        "route": None,
        "runtime": {
            "secret_visible": "WORKLOOP_SECRET_CANARY" in os.environ,
            "safe_flag_visible": os.environ.get("SAFE_EVAL_FLAG") == "explicit-value",
        },
        "usage": {"input_tokens": 0, "output_tokens": 0},
    },
    sys.stdout,
)
