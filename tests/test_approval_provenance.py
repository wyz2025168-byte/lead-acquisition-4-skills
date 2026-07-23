from __future__ import annotations

import unittest

from tests._helpers import error_codes, fresh_runtime, set_node, source


class ApprovalProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary, self.runtime = fresh_runtime()
        source(self.runtime)
        set_node(self.runtime, "B0", "NEEDS_APPROVAL")

    def tearDown(self):
        self.temporary.cleanup()

    def test_r06_ambiguous_continue_is_not_direction_approval(self):
        self.runtime.add_ndjson(
            "approvals",
            {
                "target_id": "NODE-B0",
                "approval_type": "DIRECTION",
                "user_quote": "可以继续看看",
                "interpreted_scope": "批准结果合同",
                "explicit_exclusions": [],
                "assumptions_acknowledged": [],
                "source_turn_or_file": "turn-6",
                "status": "ACTIVE",
            },
        )
        self.assertIn("E-APPROVAL-NO-PROVENANCE", error_codes(self.runtime.validate()))

    def test_precise_experiment_approval_does_not_approve_direction(self):
        approval = self.runtime.add_approval(
            {
                "target_id": "NODE-B0",
                "approval_type": "EXPERIMENT",
                "user_quote": "只批准用三次访谈验证，不批准方向和发布",
                "interpreted_scope": "三次访谈实验",
                "explicit_exclusions": ["方向批准", "生产批准", "发布"],
                "assumptions_acknowledged": ["结果合同仍是假设"],
                "source_turn_or_file": "turn-7",
                "status": "ACTIVE",
            }
        )
        self.assertEqual("EXPERIMENT", approval["approval_type"])


if __name__ == "__main__":
    unittest.main()
