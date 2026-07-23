from __future__ import annotations

import unittest

from tests._helpers import approved_outcome, error_codes, fresh_runtime, set_node, source, valid_alternative


class BusinessInvariantTests(unittest.TestCase):
    def setUp(self):
        self.temporary, self.runtime = fresh_runtime()
        source(self.runtime)

    def tearDown(self):
        self.temporary.cleanup()

    def test_r01_leading_event_cannot_be_success(self):
        outcome = approved_outcome(self.runtime, "到店")
        result = self.runtime.validate()
        self.assertIn("E-OUTCOME-SUBSTITUTION", error_codes(result))

    def test_r02_inside_out_persona_is_blocked(self):
        approved_outcome(self.runtime)
        self.runtime.add_ndjson(
            "decisions",
            {
                "statement": "负责人负责预约接待，所以客户会购买",
                "decision_type": "PERSONA",
                "business_stage": "POSITIONING",
                "target_node": "NODE-B7",
                "method_refs": ["conversion-journey"],
                "alternatives": ["ALT-1", "ALT-2", "ALT-3"],
                "selected_path": "ALT-1",
                "rationale_summary": "内部职责推导",
                "evidence_refs": ["SRC-LOCAL"],
                "counterevidence": ["客户可能不理解该职务"],
                "depends_on": [],
                "upstream_impacts": [],
                "downstream_impacts": ["NODE-C1"],
                "horizon_30d": "验证客户是否感知",
                "horizon_90d": "若不成立则停止该路线",
                "approval_state": "DIRECTION",
                "status": "ACTIVE",
                "customer_side_test": {
                    "passes_title_free": False,
                    "customer_barrier": "UNKNOWN",
                    "perceivable_behavior": "内部负责预约",
                    "why_not_any_peer": "UNKNOWN",
                    "disconfirming_signal": "删除头衔后理由消失",
                },
            },
        )
        self.assertIn("E-PERSONA-INSIDE-OUT", error_codes(self.runtime.validate()))

    def test_r03_content_before_audience_is_blocked(self):
        approved_outcome(self.runtime)
        set_node(self.runtime, "C1", "APPROVED")
        self.assertIn("E-CONTENT-BEFORE-AUDIENCE", error_codes(self.runtime.validate()))

    def test_r04_external_research_cannot_rank_local_audience(self):
        approved_outcome(self.runtime)
        source(self.runtime, "SRC-GENERAL", "E4_RESEARCH_ANALOG", "general")
        for number in range(1, 4):
            self.runtime.add_object("alternatives", valid_alternative(f"ALT-B5-{number}", "NODE-B5", "SRC-GENERAL"))
        set_node(self.runtime, "B4", "APPROVED")
        set_node(self.runtime, "B5", "APPROVED", [f"ALT-B5-{n}" for n in range(1, 4)], evidence_refs=["SRC-GENERAL"], decision_scope={"locality": "local"})
        self.assertIn("E-LOCAL-RANKING-BY-GENERAL-RESEARCH", error_codes(self.runtime.validate()))

    def test_r07_online_convertibility_unknown_blocks_audience(self):
        approved_outcome(self.runtime)
        set_node(self.runtime, "B5", "APPROVED")
        self.assertIn("E-ONLINE-CONVERTIBILITY-UNKNOWN", error_codes(self.runtime.validate()))

    def test_r08_w6_candidates_allow_exploration_with_warning(self):
        approved_outcome(self.runtime)
        alternatives = []
        for number in range(1, 4):
            item = self.runtime.add_object("alternatives", valid_alternative(f"ALT-B7-{number}", "NODE-B7"))
            alternatives.append(item["candidate_id"])
        set_node(self.runtime, "B7", "NEEDS_EVIDENCE", alternatives)
        result = self.runtime.validate()
        self.assertNotIn("E-PERSONA-BEFORE-W3-W6", error_codes(result))
        self.assertIn("W-W6-UNKNOWN", {item["code"] for item in result["business_warnings"]})

    def test_r14_leading_event_is_legal_when_not_success(self):
        approved_outcome(self.runtime)
        result = self.runtime.validate()
        self.assertNotIn("E-OUTCOME-SUBSTITUTION", error_codes(result))

    def test_r12_external_research_conflict_does_not_override_local_fact(self):
        source(self.runtime, "SRC-EXTERNAL", "E4_RESEARCH_ANALOG", "general")
        local = self.runtime.add_ndjson(
            "claims",
            {
                "claim_id": "CLM-LOCAL",
                "statement": "本地一手记录不支持外部排序",
                "subject": "audience-ranking",
                "truth_status": "CONFIRMED_FACT",
                "evidence_level": "E1_LOCAL_EXACT",
                "source_refs": ["SRC-LOCAL"],
                "scope": {"locality": "local"},
                "time_validity": "2026-Q3",
                "counterevidence": ["CLM-EXTERNAL"],
                "confidence": 0.8,
                "derived_from": [],
                "conflicts_with": ["CLM-EXTERNAL"],
            },
        )
        self.runtime.add_ndjson(
            "claims",
            {
                "claim_id": "CLM-EXTERNAL",
                "statement": "外部研究提出相反排序候选",
                "subject": "audience-ranking",
                "truth_status": "SUPPORTED_HYPOTHESIS",
                "evidence_level": "E4_RESEARCH_ANALOG",
                "source_refs": ["SRC-EXTERNAL"],
                "scope": {"locality": "general"},
                "time_validity": "2026-Q3",
                "counterevidence": ["CLM-LOCAL"],
                "confidence": 0.5,
                "derived_from": [],
                "conflicts_with": ["CLM-LOCAL"],
            },
        )
        warnings = {item["code"] for item in self.runtime.validate()["business_warnings"]}
        self.assertIn("W-RESEARCH-CONFLICT", warnings)
        self.assertFalse(local["stale"])

    def test_r13_customer_side_persona_passes_title_free_test(self):
        approved_outcome(self.runtime)
        self.runtime.add_ndjson(
            "decisions",
            {
                "statement": "人物用客户可观察行为降低方案不可逆风险",
                "decision_type": "PERSONA",
                "business_stage": "POSITIONING",
                "target_node": "NODE-B7",
                "method_refs": ["conversion-journey"],
                "alternatives": ["ALT-1", "ALT-2", "ALT-3"],
                "selected_path": "ALT-1",
                "rationale_summary": "客户侧机制",
                "evidence_refs": ["SRC-LOCAL"],
                "counterevidence": ["客户未感知该行为"],
                "depends_on": [],
                "upstream_impacts": [],
                "downstream_impacts": ["NODE-C1"],
                "horizon_30d": "验证可感知行为",
                "horizon_90d": "只在交易结果支持时扩展",
                "approval_state": "UNAPPROVED",
                "status": "ACTIVE",
                "customer_side_test": {
                    "passes_title_free": True,
                    "customer_barrier": "担心不可逆决定缺少充分解释",
                    "perceivable_behavior": "主动展示替代、限制和失败条件",
                    "why_not_any_peer": "连续记录显示该行为稳定发生",
                    "disconfirming_signal": "客户仍无法复述取舍或交易结果不改善",
                },
            },
        )
        self.assertNotIn("E-PERSONA-INSIDE-OUT", error_codes(self.runtime.validate()))


if __name__ == "__main__":
    unittest.main()
