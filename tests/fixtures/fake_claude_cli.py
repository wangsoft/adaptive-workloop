#!/usr/bin/env python3
"""Fake Claude Code CLI that validates adapter isolation flags."""

from __future__ import annotations

import json
import sys
from pathlib import Path


args = sys.argv[1:]
for flag in (
    "-p",
    "--bare",
    "--json-schema",
    "--output-format",
    "--no-session-persistence",
    "--strict-mcp-config",
):
    assert flag in args
assert args[args.index("--output-format") + 1] == "stream-json"
workspace = Path.cwd()
assert (workspace / ".claude" / "skills" / "adaptive-workloop" / "SKILL.md").is_file()
prompt = sys.stdin.read()
assert "expected" not in prompt.lower()
artifact = workspace / "review.md"
artifact.write_text("# Independent review required\n", encoding="utf-8")
for name in ("goal.json", "plan.json"):
    (workspace / name).write_text(f'{{"fixture": "{name}"}}\n', encoding="utf-8")
print(
    json.dumps(
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Skill",
                        "input": {"skill": "adaptive-workloop"},
                    }
                ]
            },
        }
    )
)
print(
    json.dumps(
        {
            "type": "result",
            "model": "claude-fable-fixture-observed",
            "structured_output": {
                "schema": "workloop-provider-result/1",
                "activated": True,
                "route": "reviewed",
                "terminal": "needs_human",
                "degradation": "labeled-self-review",
                "transcript": "fixture Claude stopped at the human boundary",
                "artifact_paths": ["goal.json", "plan.json", "review.md"],
            },
            "usage": {
                "input_tokens": 13,
                "cache_read_input_tokens": 2,
                "output_tokens": 9,
            },
            "total_cost_usd": 0.001,
        }
    )
)
