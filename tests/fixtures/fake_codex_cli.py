#!/usr/bin/env python3
"""Fake Codex CLI that validates adapter isolation flags."""

from __future__ import annotations

import json
import sys
from pathlib import Path


args = sys.argv[1:]
required_flags = {
    "--ephemeral",
    "--ignore-user-config",
    "--json",
    "--output-schema",
    "--sandbox",
}
assert required_flags.issubset(args)
assert "--dangerously-bypass-approvals-and-sandbox" not in args
assert "--ignore-rules" not in args
output_path = Path(args[args.index("-o") + 1])
workspace = Path.cwd()
skill_installed = (
    workspace / ".agents" / "skills" / "adaptive-workloop" / "SKILL.md"
).is_file()
prompt = sys.stdin.read()
assert "expected" not in prompt.lower()
artifact_paths = []
if skill_installed:
    artifact = workspace / "evidence" / "grading.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text('{"passed": true}\n', encoding="utf-8")
    artifact_paths.append("evidence/grading.json")
output_path.write_text(
    json.dumps(
        {
            "schema": "workloop-provider-result/1",
            "activated": skill_installed,
            "route": "verified" if skill_installed else None,
            "terminal": "complete",
            "degradation": "host-native-verified" if skill_installed else None,
            "transcript": "fixture codex completed the verified route",
            "artifact_paths": artifact_paths,
        }
    ),
    encoding="utf-8",
)
if skill_installed:
    print(
        json.dumps(
            {
                "type": "tool_call",
                "name": "Skill",
                "input": {"skill": "adaptive-workloop"},
            }
        )
    )
print(
    json.dumps(
        {
            "type": "turn.completed",
            "model": "gpt-fixture-observed",
            "usage": {"input_tokens": 11, "cached_input_tokens": 3, "output_tokens": 7},
        }
    )
)
