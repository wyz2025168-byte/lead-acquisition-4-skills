from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = ROOT / "skills" / "jw" / "scripts" / "jw_project.py"
SPEC = importlib.util.spec_from_file_location("jw_project_v4", RUNTIME_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)
ProjectRuntime = MODULE.ProjectRuntime


def fresh_runtime() -> tuple[tempfile.TemporaryDirectory[str], object]:
    temporary = tempfile.TemporaryDirectory()
    runtime = ProjectRuntime(Path(temporary.name))
    runtime.initialize("PRJ-TEST", "Synthetic test")
    return temporary, runtime


def source(runtime, source_id: str = "SRC-LOCAL", level: str = "E1_LOCAL_EXACT", locality: str = "local"):
    return runtime.add_object(
        "sources",
        {
            "source_id": source_id,
            "source_type": "synthetic",
            "title": source_id,
            "observed_at": "2026-07-23",
            "evidence_level": level,
            "privacy": "SYNTHETIC",
            "scope": {"locality": locality, "claim_scope": locality},
            "cannot_prove": ["未经项目证据不能证明正价成交"],
        },
    )


def approved_outcome(runtime, success_name: str = "按业务正价口径完成付款"):
    return runtime.set_outcome(
        {
            "id": "OUTCOME-001",
            "version": 1,
            "core_offer": {
                "name": "合成服务",
                "scope": "已定义核心交付",
                "price_basis": "项目方正价口径",
                "capacity_constraints": ["每月容量有限"],
                "material_exclusions": ["咨询不是成交"],
            },
            "success_event": {
                "name": success_name,
                "definition": "客户按批准的正价口径完成真实价值交换",
                "event_category": "VALUE_EXCHANGE",
                "requires_full_price": True,
                "evidence_required": ["付款或等价价值交换记录"],
                "attribution_window": "30 days",
            },
            "leading_events": [
                {"name": "咨询", "purpose": "识别意向", "not_success_reason": "尚未发生价值交换"},
                {"name": "预约", "purpose": "推进下一步", "not_success_reason": "可能未到场或未付款"},
                {"name": "到店", "purpose": "完成线下环节", "not_success_reason": "可能仍拒绝方案"},
            ],
            "excluded_success_events": ["咨询", "预约", "到店", "留资", "方案沟通"],
            "economics": {
                "minimum_viable_margin_basis": "真实项目口径",
                "capacity_basis": "真实交付容量",
                "repeatability_basis": "连续交易验证",
            },
            "status": "APPROVED",
            "sources": ["SRC-LOCAL"],
            "approved_by": "user",
            "approved_at": "2026-07-23T00:00:00Z",
        }
    )


def valid_alternative(candidate_id: str, target_node: str, source_ref: str = "SRC-LOCAL") -> dict:
    return {
        "candidate_id": candidate_id,
        "target_node": target_node,
        "statement": f"候选 {candidate_id}",
        "mechanism": "通过可观察的客户侧机制改变当前决策",
        "supporting_evidence": [source_ref],
        "counterevidence": ["存在相反交易记录的可能"],
        "unknowns": ["真实转化幅度"],
        "online_convertibility": {
            "reachable": "YES",
            "identifiable": "YES",
            "influenceable": "YES",
            "attributable": "UNKNOWN",
        },
        "smallest_disconfirming_test": "检查 3 条相反结果记录或进行 3 次目标访谈",
        "decision_effect": "决定是否选择该目标人和阶段",
    }


def set_node(runtime, code: str, status: str, alternatives: list[str] | None = None, **extra):
    payload = {
        "node_id": f"NODE-{code}",
        "code": code,
        "status": status,
        "summary": extra.pop("summary", f"{code} synthetic conclusion"),
        "method_refs": extra.pop("method_refs", ["orchestration-control"]),
        "evidence_refs": extra.pop("evidence_refs", ["SRC-LOCAL"]),
        "counterevidence": extra.pop("counterevidence", ["synthetic counterevidence"]),
        "alternative_ids": alternatives or [],
        "invalidation_conditions": extra.pop("invalidation_conditions", ["new contradictory evidence"]),
        "approval_state": extra.pop("approval_state", "UNAPPROVED"),
        **extra,
    }
    return runtime.add_object("nodes", payload, replace=True)


def error_codes(result: dict) -> set[str]:
    return {item["code"] for item in result.get("business_errors", [])}
