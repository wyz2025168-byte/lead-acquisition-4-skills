from __future__ import annotations

import unittest

from tests._helpers import approved_outcome, fresh_runtime, set_node, source


class NodeDependencyTests(unittest.TestCase):
    def setUp(self):
        self.temporary, self.runtime = fresh_runtime()
        source(self.runtime)

    def tearDown(self):
        self.temporary.cleanup()

    def test_preflight_lists_missing_dependencies(self):
        result = self.runtime.preflight("C1")
        self.assertIn("NODE-B5", result["blocking_dependency_ids"])
        self.assertTrue(result["minimal_repairs"])

    def test_b1_cannot_be_approved_before_b0(self):
        result = self.runtime.preflight("B1")
        self.assertFalse(result["allowed"])
        self.assertIn("NODE-B0", result["blocking_dependency_ids"])

    def test_r09_upstream_correction_only_invalidates_descendants(self):
        approved_outcome(self.runtime)
        set_node(self.runtime, "B0", "APPROVED")
        set_node(self.runtime, "B1", "APPROVED")
        set_node(self.runtime, "B2", "APPROVED")
        set_node(self.runtime, "B3", "APPROVED")
        set_node(self.runtime, "B4", "APPROVED")
        result = self.runtime.invalidate(["NODE-B0"], "到店不是成交")
        self.assertIn("NODE-C1", result["affected_ids"])
        self.assertNotIn("SRC-LOCAL", result["affected_ids"])

    def test_r10_natural_first_turn_stops_at_b0(self):
        status = self.runtime.status()
        self.assertEqual("NODE-B0", status["current_node"])
        self.assertEqual("UNKNOWN", status["node_status"]["B0"])


if __name__ == "__main__":
    unittest.main()
