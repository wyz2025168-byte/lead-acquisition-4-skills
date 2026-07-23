#!/usr/bin/env python3
"""Run a de-identified high-ticket dental semantic replay."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKS = {
    "defines_real_value_exchange_first": "tests.test_business_invariants.BusinessInvariantTests.test_r01_leading_event_cannot_be_success",
    "separates_transaction_roles": "tests.test_node_dependencies.NodeDependencyTests.test_r10_natural_first_turn_stops_at_b0",
    "checks_online_convertibility": "tests.test_business_invariants.BusinessInvariantTests.test_r07_online_convertibility_unknown_blocks_audience",
    "does_not_rank_local_audience_by_general_research": "tests.test_business_invariants.BusinessInvariantTests.test_r04_external_research_cannot_rank_local_audience",
    "does_not_treat_visit_as_success": "tests.test_business_invariants.BusinessInvariantTests.test_r14_leading_event_is_legal_when_not_success",
    "rejects_internal_duty_as_purchase_reason": "tests.test_business_invariants.BusinessInvariantTests.test_r02_inside_out_persona_is_blocked",
    "keeps_w6_candidates_when_unknown": "tests.test_business_invariants.BusinessInvariantTests.test_r08_w6_candidates_allow_exploration_with_warning",
    "blocks_content_before_audience": "tests.test_business_invariants.BusinessInvariantTests.test_r03_content_before_audience_is_blocked",
    "asks_minimum_decision_changing_information": "tests.test_minimum_information.MinimumInformationTests.test_r11_no_history_data_uses_nonblocking_fallback",
    "invalidates_only_true_descendants": "tests.test_node_dependencies.NodeDependencyTests.test_r09_upstream_correction_only_invalidates_descendants"
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "evals" / "replay" / "SYNTHETIC_REPLAY_SUMMARY.json"))
    args = parser.parse_args()
    results = []
    for name, test_id in CHECKS.items():
        process = subprocess.run([sys.executable, "-m", "unittest", test_id], cwd=ROOT, text=True, capture_output=True)
        raw = process.stdout + process.stderr
        results.append({"check": name, "test_id": test_id, "status": "PASS" if process.returncode == 0 else "FAIL", "output_sha256": hashlib.sha256(raw.encode()).hexdigest()})
    summary = {
        "schema_version": "jw.synthetic-replay.v1",
        "scenario": "deidentified_local_high_ticket_dental",
        "private_project_answers_used": False,
        "checks": results,
        "passed": sum(item["status"] == "PASS" for item in results),
        "failed": sum(item["status"] == "FAIL" for item in results),
        "status": "PASS" if all(item["status"] == "PASS" for item in results) else "FAIL"
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
