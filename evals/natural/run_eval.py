#!/usr/bin/env python3
"""Validate natural-eval isolation and freeze a reproducible run manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVAL_ROOT = Path(__file__).resolve().parent
SCENARIOS = EVAL_ROOT / "scenarios"
RUBRIC = EVAL_ROOT / "rubric.json"
PROMPT_LEAKAGE = (
    r"必须输出.*阶段", r"必须给.*选题", r"A/B.*开头", r"指定.*CTA",
    r"错误码", r"NODE-B[0-7]", r"先做 B0", r"调用.*method",
)
FIXTURE_POLLUTION = (
    "\u884c\u653f\u9662\u957f", "\u6280\u672f\u9662\u957f", "\u6210\u5e74\u5b50\u5973\u7b2c\u4e00",
    "\u68c0\u67e5\u6e05\u5355 CTA", "\u6bcf\u5468 6 \u6761",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan", action="store_true")
    parser.add_argument("--manifest", default=str(EVAL_ROOT / "RUN_MANIFEST.json"))
    args = parser.parse_args()
    rubric = json.loads(RUBRIC.read_text(encoding="utf-8"))
    scenario_files = sorted(SCENARIOS.glob("*.md"))
    failures = []
    for path in scenario_files:
        text = path.read_text(encoding="utf-8")
        for pattern in PROMPT_LEAKAGE:
            if re.search(pattern, text, re.I):
                failures.append({"file": path.name, "type": "PROMPT_LEAKAGE", "pattern": pattern})
        for marker in FIXTURE_POLLUTION:
            if marker in text:
                failures.append({"file": path.name, "type": "FIXTURE_POLLUTION", "marker": marker})
    manifest = {
        "schema_version": "jw.natural-eval-manifest.v1",
        "rubric_version": rubric["version"],
        "rubric_sha256": sha256(RUBRIC),
        "scenario_count": len(scenario_files),
        "scenarios": [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path)} for path in scenario_files],
        "generator_visibility": "scenario + candidate skill only",
        "judge_visibility": "anonymous output + frozen rubric only",
        "implementation_details_visible_to_judge": False,
        "scan_failures": failures,
        "status": "PASS" if len(scenario_files) >= 7 and not failures else "FAIL",
        "note": "This manifest validates isolation and freeze state; model execution evidence is stored outside the public package.",
    }
    Path(args.manifest).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
