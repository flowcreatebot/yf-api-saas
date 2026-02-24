#!/usr/bin/env python3
import json
import pathlib
import subprocess
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
report_json = ROOT / "reports" / "latest_test_status.json"

status = "unknown"
run_at = "n/a"
if report_json.exists():
    try:
        data = json.loads(report_json.read_text())
        status = data.get("status", "unknown")
        run_at = data.get("timestamp", "n/a")
    except Exception:
        pass

def sh(cmd: str) -> str:
    p = subprocess.run(cmd, shell=True, cwd=ROOT, text=True, capture_output=True)
    return (p.stdout or "").strip()

branch = sh("git rev-parse --abbrev-ref HEAD || true") or "n/a"
short_sha = sh("git rev-parse --short HEAD || true") or "n/a"
changes = sh("git status --short | wc -l") or "0"

badge = "✅" if status == "green" else ("❌" if status == "red" else "⚪")

card = f"""📊 **YF API SaaS Status Card**
- Test Suite: {badge} ({status})
- Last Test Run: {run_at}
- Branch/Rev: `{branch}` / `{short_sha}`
- Working Tree Changes: {changes}
- Updated: {datetime.now().isoformat(timespec='seconds')}
"""

print(card)
