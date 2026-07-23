from __future__ import annotations

import unittest

from tests._helpers import error_codes, fresh_runtime, source


class MinimumInformationTests(unittest.TestCase):
    def setUp(self):
        self.temporary, self.runtime = fresh_runtime()
        source(self.runtime)

    def tearDown(self):
        self.temporary.cleanup()

    def test_r05_request_without_decision_and_oversized_is_blocked(self):
        self.runtime.add_object(
            "information_requests",
            {
                "request_id": "IRQ-001",
                "question": "整理过去12个月全部客户明细",
                "target_decision": "",
                "current_alternatives": [],
                "how_answer_changes_decision": "",
                "minimum_sample": "12个月全部记录",
                "why_smaller_is_insufficient": "",
                "fallback_if_unavailable": "停止项目",
                "blocking": True,
            },
        )
        codes = error_codes(self.runtime.validate())
        self.assertIn("E-DATA-REQUEST-NO-DECISION", codes)
        self.assertIn("E-DATA-REQUEST-OVERSIZED", codes)

    def test_r11_no_history_data_uses_nonblocking_fallback(self):
        self.runtime.add_object(
            "information_requests",
            {
                "request_id": "IRQ-002",
                "question": "提供最近3条成交和3条未成交的脱敏节点记录（若有）",
                "target_decision": "NODE-B5",
                "current_alternatives": ["ALT-1", "ALT-2"],
                "how_answer_changes_decision": "区分目标人还是承接环节更早失效",
                "minimum_sample": "每类最多3条可用记录",
                "why_smaller_is_insufficient": "单条无法区分偶发与重复机制",
                "fallback_if_unavailable": "保留两个假设并做3次目标访谈",
                "blocking": False,
            },
        )
        self.assertNotIn("E-DATA-REQUEST-OVERSIZED", error_codes(self.runtime.validate()))


if __name__ == "__main__":
    unittest.main()
