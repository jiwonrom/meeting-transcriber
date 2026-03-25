#!/usr/bin/env python3
"""Stop hook — 작업 완료 시 phase gate 검증."""
import subprocess
import sys

checks = {
    "lint": "ruff check src/",
    "typecheck": "mypy src/ --ignore-missing-imports",
    "test": "pytest tests/ -x --tb=short -q",
}

failed = []
for name, cmd in checks.items():
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        failed.append(name)
        output = result.stdout.strip() or result.stderr.strip()
        print(f"❌ {name}: {output[:200]}", file=sys.stderr)

if failed:
    print(f"\n❌ Phase gate FAILED: {', '.join(failed)}", file=sys.stderr)
    print("위 체크를 통과하도록 수정하라.", file=sys.stderr)
    sys.exit(1)
else:
    print("✅ Phase gate PASSED", file=sys.stderr)
