#!/usr/bin/env python3
"""Spawn a delayed child so timeout tests can detect orphaned processes."""

from __future__ import annotations

import os
import subprocess
import sys
import time


marker = os.environ["CHILD_MARKER"]
subprocess.Popen(
    [
        sys.executable,
        "-c",
        (
            "import pathlib,time; "
            "time.sleep(0.4); "
            f"pathlib.Path({marker!r}).write_text('orphan', encoding='utf-8')"
        ),
    ]
)
time.sleep(10)
