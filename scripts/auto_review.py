#!/usr/bin/env python3
"""PostToolUse hook — 파일 수정 후 자동 lint/typecheck."""
import subprocess
import sys

checks = [
    ("ruff check src/ --fix", "lint"),
    ("mypy src/ --ignore-missing-imports --no-error-summary", "typecheck"),
]

for cmd, name in checks:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        output = result.stdout.strip() or result.stderr.strip()
        if output:
            print(f"⚠️ {name}:\n{output[:500]}", file=sys.stderr)
