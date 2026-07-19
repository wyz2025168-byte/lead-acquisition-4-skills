#!/usr/bin/env python3
"""Validate one installed Skill bundle using its local manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "BUNDLE_MANIFEST.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not MANIFEST.is_file():
        raise SystemExit("FAIL: BUNDLE_MANIFEST.json missing")
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures: list[str] = []
    for item in data.get("files", []):
        path = ROOT / item["path"]
        if not path.is_file():
            failures.append(f"missing:{item['path']}")
            continue
        if sha256(path) != item["sha256"]:
            failures.append(f"hash:{item['path']}")
    if failures:
        raise SystemExit("FAIL: " + ", ".join(failures))
    print(json.dumps({"skill": data.get("skill"), "files": len(data.get("files", [])), "result": "PASS"}, ensure_ascii=False))


if __name__ == "__main__":
    main()

