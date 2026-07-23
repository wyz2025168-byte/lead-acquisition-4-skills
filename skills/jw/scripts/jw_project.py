#!/usr/bin/env python3
"""Deterministic v4 runtime for the public $jw business reasoning system."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUNTIME_VERSION = "4.0.0-rc.1"
STATE_SCHEMA = "jw.project-state.v4"
REGISTRY_SCHEMA = "4.0.0"
STAGES = ("POSITIONING", "CONTENT", "PRODUCTION", "PORTFOLIO", "OPERATIONS")
STAGE_ORDER = {stage: index for index, stage in enumerate(STAGES)}
EVIDENCE_LEVELS = {
    "E1_LOCAL_EXACT",
    "E2_LOCAL_ADJACENT",
    "E3_EXTERNAL_SAME_PATTERN",
    "E4_RESEARCH_ANALOG",
    "E5_PROJECT_JUDGMENT",
    "E6_AI_HYPOTHESIS",
}
TRUTH_STATUSES = {
    "CONFIRMED_FACT",
    "SUPPORTED_HYPOTHESIS",
    "UNVERIFIED",
    "DISPUTED",
    "REJECTED",
}
APPROVAL_TYPES = {"DIRECTION", "EXPERIMENT", "ARTIFACT", "PUBLISH"}
LEGACY_APPROVAL_TYPES = {
    "FACT_CONFIRMED",
    "HYPOTHESIS_ACCEPTED",
    "EXPERIMENT_AUTHORIZED",
    "PRODUCTION_APPROVED",
}
NEXT_ACTION_FIELDS = {
    "owner",
    "minimum_input",
    "timebox",
    "artifact",
    "decision_threshold",
    "stop_rule",
    "expansion_condition",
}
NDJSON_FILES = {
    "claims": ("claims.ndjson", "claim_id", "CLM"),
    "decisions": ("decisions.ndjson", "decision_id", "DEC"),
    "approvals": ("approvals.ndjson", "approval_id", "APR"),
    "experiments": ("experiments.ndjson", "experiment_id", "EXP"),
    "feedback": ("feedback.ndjson", "feedback_id", "FDB"),
}
OBJECT_FILES = {
    "sources": ("source-registry.json", "source_id", "SRC"),
    "entities": ("entities.json", "entity_id", "ENT"),
    "artifacts": ("artifact-registry.json", "artifact_id", "ART"),
    "content": ("content-inventory.json", "content_id", "CNT"),
    "outcomes": ("outcome-contracts.json", "id", "OUTCOME"),
    "nodes": ("business-nodes.json", "node_id", "NODE"),
    "alternatives": ("alternatives.json", "candidate_id", "ALT"),
    "information_requests": ("information-requests.json", "request_id", "IRQ"),
}
FORBIDDEN_VAGUE = ("若干", "足量", "适当", "尽量")
DECISION_STATUSES = {"ACTIVE", "REJECTED", "NEEDS_REQUALIFICATION", "SUPERSEDED"}
APPROVAL_STATES = {"UNAPPROVED", "DIRECTION", "EXPERIMENT", "ARTIFACT", "PUBLISH", "NEEDS_RECONFIRMATION"}
NODE_STATUSES = {"UNKNOWN", "HYPOTHESIS", "NEEDS_EVIDENCE", "NEEDS_APPROVAL", "APPROVED", "INVALIDATED", "SUPERSEDED"}
NODE_ORDER = ("B0", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "C1", "C2", "P1", "O1")
NODE_NAMES = {
    "B0": "结果合同",
    "B1": "业务/产品边界",
    "B2": "交易角色链",
    "B3": "购买触发与阶段",
    "B4": "线上可转化性",
    "B5": "W1/W2 目标人和阶段",
    "B6": "W3/W4 信任与选择理由",
    "B7": "W5/W6 行动与付款理由",
    "C1": "内容策略",
    "C2": "四圈与脚本",
    "P1": "生产呈现",
    "O1": "组合与运营",
}
NODE_DEPENDENCIES = {
    "B0": [],
    "B1": ["B0"],
    "B2": ["B1"],
    "B3": ["B1", "B2"],
    "B4": ["B2", "B3"],
    "B5": ["B0", "B1", "B2", "B3", "B4"],
    "B6": ["B5"],
    "B7": ["B5", "B6"],
    "C1": ["B0", "B5", "B6", "B7"],
    "C2": ["C1"],
    "P1": ["C2"],
    "O1": ["B0", "C1", "P1"],
}
NODE_STAGE = {
    "B0": "POSITIONING", "B1": "POSITIONING", "B2": "POSITIONING", "B3": "POSITIONING",
    "B4": "POSITIONING", "B5": "POSITIONING", "B6": "POSITIONING", "B7": "POSITIONING",
    "C1": "CONTENT", "C2": "CONTENT", "P1": "PRODUCTION", "O1": "OPERATIONS",
}
AMBIGUOUS_APPROVAL_QUOTES = {"可以继续看看", "继续看看", "先看看", "可以继续", "继续推进", "可以"}


class RuntimeErrorUser(Exception):
    """A safe, user-facing runtime error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return copy.deepcopy(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeErrorUser(f"无法读取 {path}: {error}") from error


def write_json(path: Path, value: Any) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def read_ndjson(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise RuntimeErrorUser(f"{path}:{line_number} 不是有效 JSON: {error}") from error
        if not isinstance(record, dict):
            raise RuntimeErrorUser(f"{path}:{line_number} 必须是对象")
        records.append(record)
    return records


def append_ndjson(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def latest_by(records: list[dict[str, Any]], id_field: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for record in records:
        identifier = record.get(id_field)
        if isinstance(identifier, str):
            result[identifier] = record
    return result


def without_hash(value: dict[str, Any]) -> dict[str, Any]:
    cleaned = copy.deepcopy(value)
    cleaned.pop("payload_hash", None)
    cleaned.pop("state_hash", None)
    return cleaned


def stamped_record(
    payload: dict[str, Any], *, identifier_field: str, prefix: str, previous: dict[str, Any] | None = None
) -> dict[str, Any]:
    record = copy.deepcopy(payload)
    now = utc_now()
    if not record.get(identifier_field):
        seed = {"payload": record, "now": now, "pid": os.getpid()}
        record[identifier_field] = f"{prefix}-{digest_value(seed)[:12].upper()}"
    if previous:
        record["created_at"] = previous.get("created_at", now)
        record["revision"] = int(previous.get("revision", 1)) + 1
    else:
        record["created_at"] = now
        record["revision"] = 1
    record["updated_at"] = now
    record.setdefault("stale", False)
    record["payload_hash"] = digest_value(without_hash(record))
    return record


def stamped_state(state: dict[str, Any], *, previous: dict[str, Any] | None = None) -> dict[str, Any]:
    result = copy.deepcopy(state)
    now = utc_now()
    result["updated_at"] = now
    result["revision"] = int((previous or result).get("revision", 0)) + 1
    result["state_hash"] = digest_value(without_hash(result))
    return result


def parse_json_argument(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeErrorUser(f"--json 不是有效 JSON: {error}") from error
    if not isinstance(value, dict):
        raise RuntimeErrorUser("--json 必须是 JSON 对象")
    return value


def require(record: dict[str, Any], fields: set[str], label: str) -> None:
    missing = sorted(field for field in fields if field not in record or record[field] in (None, ""))
    if missing:
        raise RuntimeErrorUser(f"{label} 缺少字段: {', '.join(missing)}")


def is_expired(value: str | None) -> bool:
    if not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise RuntimeErrorUser(f"无效时间: {value}")
    return parsed < datetime.now(timezone.utc)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items() if key not in {"raw_content", "content", "phone", "wechat", "address", "medical_record"}}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if not isinstance(value, str):
        return value
    text = re.sub(r"(?<!\d)1[3-9]\d{9}(?!\d)", "[REDACTED_PHONE]", value)
    text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", text)
    text = re.sub(r"\b(?:微信|WeChat|wx)[:：\s]*[A-Za-z0-9_-]{5,}\b", "[REDACTED_WECHAT]", text, flags=re.I)
    return text


class ProjectRuntime:
    def __init__(self, project_root: Path | str):
        self.project_root = Path(project_root).expanduser().resolve()
        self.root = self.project_root / ".jw-project"

    @property
    def state_path(self) -> Path:
        return self.root / "project-state.json"

    @property
    def skill_dir(self) -> Path:
        return Path(__file__).resolve().parents[1]

    @property
    def registry_path(self) -> Path:
        return self.skill_dir / "references" / "method-registry.json"

    @property
    def invariant_path(self) -> Path:
        return self.skill_dir / "references" / "business-invariants.json"

    def method_registry(self) -> dict[str, Any]:
        registry = load_json(self.registry_path, {})
        if not isinstance(registry, dict) or registry.get("registry_version") != REGISTRY_SCHEMA:
            raise RuntimeErrorUser("方法注册表缺失或版本不匹配")
        methods = registry.get("methods", [])
        items = registry.get("items", [])
        if not isinstance(methods, list) or len(methods) != 7:
            raise RuntimeErrorUser("方法注册表必须包含七个方法")
        method_ids = {item.get("method_id") for item in methods}
        if len(method_ids) != 7 or None in method_ids:
            raise RuntimeErrorUser("方法 ID 缺失或重复")
        allowed = set(registry.get("classification_enum", []))
        if allowed != {"VALID_PRINCIPLE", "PROJECT_HYPOTHESIS", "ENGINEERING_GUARD", "RETIRED"}:
            raise RuntimeErrorUser("方法资格分类不完整")
        for item in items:
            if item.get("method_id") not in method_ids or item.get("classification") not in allowed:
                raise RuntimeErrorUser(f"方法资格项无效: {item.get('item_id')}")
        return registry

    def method_ids(self) -> set[str]:
        return {item["method_id"] for item in self.method_registry()["methods"]}

    def invariant_registry(self) -> dict[str, Any]:
        registry = load_json(self.invariant_path, {})
        rules = registry.get("rules", []) if isinstance(registry, dict) else []
        required = {
            "E-OUTCOME-MISSING", "E-OUTCOME-SUBSTITUTION", "E-CONTENT-BEFORE-AUDIENCE",
            "E-PERSONA-BEFORE-W3-W6", "E-PERSONA-INSIDE-OUT",
            "E-LOCAL-RANKING-BY-GENERAL-RESEARCH", "E-ONLINE-CONVERTIBILITY-UNKNOWN",
            "E-DATA-REQUEST-NO-DECISION", "E-DATA-REQUEST-OVERSIZED",
            "E-APPROVAL-NO-PROVENANCE", "E-EVIDENCE-SCOPE-MISMATCH",
            "W-LEADING-METRIC-ONLY", "W-W6-UNKNOWN",
        }
        codes = {item.get("code") for item in rules}
        if not required.issubset(codes) or any(not all(key in item for key in ("code", "severity", "relation", "message", "minimal_repair")) for item in rules):
            raise RuntimeErrorUser("业务不变量注册表缺失或不完整")
        return registry

    def ensure_initialized(self) -> None:
        if not self.state_path.is_file():
            raise RuntimeErrorUser(f"未找到 {self.state_path}；先运行 init 或 migrate")

    def initialize(self, project_id: str, name: str) -> dict[str, Any]:
        if self.root.exists() and any(self.root.iterdir()):
            raise RuntimeErrorUser(f"{self.root} 已存在且非空；不得覆盖")
        for directory in ("sources", "artifacts", "backups", "exports"):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        for filename, _, _ in NDJSON_FILES.values():
            atomic_write(self.root / filename, "")
        for kind, (filename, _, _) in OBJECT_FILES.items():
            write_json(self.root / filename, {kind: []})
        now = utc_now()
        initial_next = {
            "owner": "project_owner",
            "minimum_input": "提供核心产品、正价口径和什么事件才算真实成功；无需预先整理全量资料",
            "timebox": "首次接管会话",
            "artifact": "B0 结果合同候选",
            "decision_threshold": "能区分真实价值交换与咨询、预约、到店等领先事件",
            "stop_rule": "出现隐私、权限、合规或关键事实冲突时停止下传",
            "expansion_condition": "只有两个结果口径会导致不同上游路径时再索取最小补充",
        }
        state = {
            "schema_version": STATE_SCHEMA,
            "runtime_version": RUNTIME_VERSION,
            "project_id": project_id,
            "project_name": name,
            "active_stage": "POSITIONING",
            "current_node": "NODE-B0",
            "current_bottleneck": "尚未批准真实业务结果合同",
            "objective_30d": {"statement": "待确定", "leading_indicators": [], "checkpoints": []},
            "forecast_90d": {"baseline": "待确定", "upside": "待确定", "risk": "待确定", "triggers": []},
            "stage_status": {stage: "NOT_STARTED" for stage in STAGES},
            "migration_status": "FRESH_V4",
            "next_action": initial_next,
            "created_at": now,
            "updated_at": now,
            "revision": 0,
        }
        state = stamped_state(state)
        write_json(self.state_path, state)
        nodes = []
        for code in NODE_ORDER:
            nodes.append(
                stamped_record(
                    {
                        "node_id": f"NODE-{code}",
                        "code": code,
                        "name": NODE_NAMES[code],
                        "business_stage": NODE_STAGE[code],
                        "status": "UNKNOWN",
                        "summary": "待判断",
                        "method_refs": ["orchestration-control"],
                        "evidence_refs": [],
                        "counterevidence": [],
                        "alternative_ids": [],
                        "depends_on": [f"NODE-{item}" for item in NODE_DEPENDENCIES[code]],
                        "invalidation_conditions": [],
                        "approval_state": "UNAPPROVED",
                    },
                    identifier_field="node_id",
                    prefix="NODE",
                )
            )
        self.write_object_records("nodes", nodes)
        self.handoff()
        return state

    def state(self) -> dict[str, Any]:
        self.ensure_initialized()
        value = load_json(self.state_path)
        if not isinstance(value, dict):
            raise RuntimeErrorUser("project-state.json 必须是对象")
        return value

    def write_state(self, changes: dict[str, Any]) -> dict[str, Any]:
        previous = self.state()
        value = copy.deepcopy(previous)
        value.update(copy.deepcopy(changes))
        value = stamped_state(value, previous=previous)
        write_json(self.state_path, value)
        return value

    def object_records(self, kind: str) -> list[dict[str, Any]]:
        filename, _, _ = OBJECT_FILES[kind]
        value = load_json(self.root / filename, {kind: []})
        records = value.get(kind, []) if isinstance(value, dict) else []
        if not isinstance(records, list):
            raise RuntimeErrorUser(f"{filename} 的 {kind} 必须是数组")
        return records

    def write_object_records(self, kind: str, records: list[dict[str, Any]]) -> None:
        filename, _, _ = OBJECT_FILES[kind]
        write_json(self.root / filename, {kind: records})

    def ndjson_latest(self, kind: str) -> dict[str, dict[str, Any]]:
        filename, id_field, _ = NDJSON_FILES[kind]
        return latest_by(read_ndjson(self.root / filename), id_field)

    def all_latest(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for kind, (filename, id_field, _) in NDJSON_FILES.items():
            for identifier, record in latest_by(read_ndjson(self.root / filename), id_field).items():
                if identifier in result:
                    raise RuntimeErrorUser(f"全局 ID 重复: {identifier}")
                result[identifier] = record
        for kind, (_, id_field, _) in OBJECT_FILES.items():
            for record in self.object_records(kind):
                identifier = record.get(id_field)
                if not isinstance(identifier, str):
                    raise RuntimeErrorUser(f"{kind} 记录缺少 {id_field}")
                if identifier in result:
                    raise RuntimeErrorUser(f"全局 ID 重复: {identifier}")
                result[identifier] = record
        return result

    def add_ndjson(self, kind: str, payload: dict[str, Any], *, revise: bool = False) -> dict[str, Any]:
        self.ensure_initialized()
        filename, id_field, prefix = NDJSON_FILES[kind]
        current = self.ndjson_latest(kind)
        identifier = payload.get(id_field)
        previous = current.get(identifier) if isinstance(identifier, str) else None
        if previous and not revise:
            raise RuntimeErrorUser(f"{identifier} 已存在；修订时使用 --revise")
        record = stamped_record(payload, identifier_field=id_field, prefix=prefix, previous=previous)
        if record[id_field] in self.all_latest() and not previous:
            raise RuntimeErrorUser(f"全局 ID 已存在: {record[id_field]}")
        self.validate_record(kind, record)
        append_ndjson(self.root / filename, record)
        self.touch_stage(record.get("business_stage"))
        self.handoff()
        return record

    def add_object(self, kind: str, payload: dict[str, Any], *, replace: bool = False) -> dict[str, Any]:
        self.ensure_initialized()
        _, id_field, prefix = OBJECT_FILES[kind]
        records = self.object_records(kind)
        index = {record.get(id_field): position for position, record in enumerate(records)}
        identifier = payload.get(id_field)
        previous = records[index[identifier]] if isinstance(identifier, str) and identifier in index else None
        if previous and not replace:
            raise RuntimeErrorUser(f"{identifier} 已存在；替换时使用 --replace")
        record = stamped_record(payload, identifier_field=id_field, prefix=prefix, previous=previous)
        if record[id_field] in self.all_latest() and not previous:
            raise RuntimeErrorUser(f"全局 ID 已存在: {record[id_field]}")
        self.validate_record(kind, record)
        if previous:
            records[index[identifier]] = record
        else:
            records.append(record)
        self.write_object_records(kind, records)
        self.touch_stage(record.get("business_stage"))
        self.handoff()
        return record

    def validate_record(self, kind: str, record: dict[str, Any]) -> None:
        stage = record.get("business_stage")
        if stage is not None and stage not in STAGES:
            raise RuntimeErrorUser(f"business_stage 必须是五阶段之一，收到 {stage}")
        if kind == "claims":
            require(record, {"statement", "subject", "truth_status", "evidence_level", "source_refs", "scope", "time_validity", "counterevidence", "confidence", "derived_from"}, "claim")
            if record["truth_status"] not in TRUTH_STATUSES:
                raise RuntimeErrorUser("无效 truth_status")
            if record["evidence_level"] not in EVIDENCE_LEVELS:
                raise RuntimeErrorUser("无效 evidence_level")
            if not isinstance(record["source_refs"], list) or not record["source_refs"]:
                raise RuntimeErrorUser("claim.source_refs 至少需要一个来源")
            if not isinstance(record["confidence"], (int, float)) or not 0 <= record["confidence"] <= 1:
                raise RuntimeErrorUser("confidence 必须在 0 到 1")
        elif kind == "decisions":
            require(record, {"statement", "business_stage", "method_refs", "alternatives", "selected_path", "rationale_summary", "evidence_refs", "counterevidence", "depends_on", "upstream_impacts", "downstream_impacts", "horizon_30d", "horizon_90d", "approval_state", "status"}, "decision")
            if not isinstance(record["alternatives"], list) or len(record["alternatives"]) < 3:
                raise RuntimeErrorUser("高影响 decision 至少需要两个候选和一个维持现状路径")
            if not isinstance(record["method_refs"], list) or not record["method_refs"]:
                raise RuntimeErrorUser("高影响 decision 至少需要一个 method_ref")
            unknown_methods = sorted(set(record["method_refs"]) - self.method_ids())
            if unknown_methods:
                raise RuntimeErrorUser(f"decision.method_refs 未注册: {unknown_methods}")
            if record["approval_state"] not in APPROVAL_STATES:
                raise RuntimeErrorUser("decision.approval_state 无效")
            if record["status"] not in DECISION_STATUSES:
                raise RuntimeErrorUser("decision.status 无效")
        elif kind == "approvals":
            require(record, {"target_id", "approval_type", "user_quote", "interpreted_scope", "explicit_exclusions", "assumptions_acknowledged", "source_turn_or_file", "status"}, "approval")
            if record["approval_type"] not in APPROVAL_TYPES:
                raise RuntimeErrorUser("无效 approval_type")
            if record["status"] not in {"ACTIVE", "REVOKED", "NEEDS_RECONFIRMATION", "INVALIDATED", "EXPIRED"}:
                raise RuntimeErrorUser("无效 approval status")
            if not isinstance(record["explicit_exclusions"], list) or not isinstance(record["assumptions_acknowledged"], list):
                raise RuntimeErrorUser("approval exclusions/assumptions 必须是数组")
            if record["approval_type"] == "PUBLISH" and record["status"] == "ACTIVE":
                require(record, {"scope"}, "发布批准")
                require(record["scope"], {"channel", "audience", "action", "valid_until", "version_refs"}, "发布批准 scope")
        elif kind == "experiments":
            require(record, {"title", "business_stage", "hypothesis_claim_ids", "owner", "minimum_input", "timebox", "artifact", "decision_threshold", "stop_rule", "expansion_condition", "depends_on", "status"}, "experiment")
            for field in ("minimum_input", "timebox", "decision_threshold", "stop_rule", "expansion_condition"):
                if any(word in str(record[field]) for word in FORBIDDEN_VAGUE):
                    raise RuntimeErrorUser(f"experiment.{field} 包含不可复现词")
            if not record["hypothesis_claim_ids"]:
                raise RuntimeErrorUser("experiment 至少需要一个 hypothesis claim")
        elif kind == "feedback":
            require(record, {"period", "metrics", "observations", "user_corrections", "repeated_questions", "execution_blocks", "plan_actual_gaps", "state_recovery", "recommended_action"}, "feedback")
        elif kind == "sources":
            require(record, {"source_type", "title", "observed_at", "evidence_level", "privacy", "scope"}, "source")
            if record["evidence_level"] not in EVIDENCE_LEVELS:
                raise RuntimeErrorUser("source.evidence_level 无效")
        elif kind == "entities":
            require(record, {"display_name", "preferred_reference", "role", "authority", "professional_boundary", "touchpoints", "capacity", "source_refs", "unknown_fields"}, "entity")
        elif kind == "artifacts":
            require(record, {"relative_path", "artifact_type", "business_stage", "method_refs", "evidence_refs", "counterevidence", "depends_on", "upstream_impacts", "downstream_impacts", "horizon_30d", "horizon_90d", "approval_state", "privacy", "status"}, "artifact")
            if not isinstance(record["method_refs"], list) or not record["method_refs"]:
                raise RuntimeErrorUser("artifact 至少需要一个 method_ref")
            unknown_methods = sorted(set(record["method_refs"]) - self.method_ids())
            if unknown_methods:
                raise RuntimeErrorUser(f"artifact.method_refs 未注册: {unknown_methods}")
            if record["approval_state"] not in APPROVAL_STATES:
                raise RuntimeErrorUser("artifact.approval_state 无效")
            relative = Path(record["relative_path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise RuntimeErrorUser("artifact.relative_path 必须位于 .jw-project 内")
            target = self.root / relative
            if not target.is_file():
                raise RuntimeErrorUser(f"成果文件不存在: {target}")
            record["content_sha256"] = sha256_file(target)
            record["bytes"] = target.stat().st_size
            record["payload_hash"] = digest_value(without_hash(record))
        elif kind == "content":
            require(record, {"title", "customer_stage", "journey_job", "target_claim_ids", "format", "planned_weight", "actual_units", "status", "artifact_refs", "depends_on"}, "content")
            if not isinstance(record["planned_weight"], (int, float)) or record["planned_weight"] < 0:
                raise RuntimeErrorUser("planned_weight 必须是非负数")
            if not isinstance(record["actual_units"], (int, float)) or record["actual_units"] < 0:
                raise RuntimeErrorUser("actual_units 必须是非负数")
            if not record["target_claim_ids"]:
                raise RuntimeErrorUser("content 至少需要一个 target claim")
        elif kind == "outcomes":
            fields = {"id", "version", "core_offer", "success_event", "leading_events", "excluded_success_events", "economics", "status", "sources", "approved_by", "approved_at"}
            missing = sorted(fields - set(record))
            if missing:
                raise RuntimeErrorUser(f"outcome contract 缺少字段: {', '.join(missing)}")
            require(record["core_offer"], {"name", "scope", "price_basis", "capacity_constraints", "material_exclusions"}, "outcome.core_offer")
            require(record["success_event"], {"name", "definition", "requires_full_price", "evidence_required", "attribution_window"}, "outcome.success_event")
            require(record["economics"], {"minimum_viable_margin_basis", "capacity_basis", "repeatability_basis"}, "outcome.economics")
            if not isinstance(record["core_offer"]["capacity_constraints"], list) or not isinstance(record["core_offer"]["material_exclusions"], list):
                raise RuntimeErrorUser("outcome.core_offer capacity_constraints/material_exclusions 必须是数组")
            if not isinstance(record["success_event"]["evidence_required"], list):
                raise RuntimeErrorUser("outcome.success_event.evidence_required 必须是数组")
            if record["status"] not in {"HYPOTHESIS", "APPROVED", "INVALIDATED"}:
                raise RuntimeErrorUser("outcome.status 无效")
            if not isinstance(record["leading_events"], list) or not isinstance(record["excluded_success_events"], list):
                raise RuntimeErrorUser("outcome leading/excluded events 必须是数组")
        elif kind == "nodes":
            require(record, {"node_id", "code", "status", "summary", "method_refs", "evidence_refs", "counterevidence", "alternative_ids", "invalidation_conditions", "approval_state"}, "business node")
            if record["code"] not in NODE_ORDER or record["node_id"] != f"NODE-{record['code']}":
                raise RuntimeErrorUser("node code/id 无效")
            if record["status"] not in NODE_STATUSES:
                raise RuntimeErrorUser("node.status 无效")
            if record["approval_state"] not in APPROVAL_STATES:
                raise RuntimeErrorUser("node.approval_state 无效")
            unknown_methods = sorted(set(record["method_refs"]) - self.method_ids())
            if unknown_methods:
                raise RuntimeErrorUser(f"node.method_refs 未注册: {unknown_methods}")
        elif kind == "alternatives":
            require(record, {"candidate_id", "target_node", "statement", "mechanism", "supporting_evidence", "counterevidence", "unknowns", "online_convertibility", "smallest_disconfirming_test", "decision_effect"}, "alternative")
            if record["target_node"] not in {f"NODE-{code}" for code in NODE_ORDER}:
                raise RuntimeErrorUser("alternative.target_node 无效")
            require(record["online_convertibility"], {"reachable", "identifiable", "influenceable", "attributable"}, "alternative.online_convertibility")
            allowed = {"YES", "NO", "UNKNOWN"}
            if any(value not in allowed for value in record["online_convertibility"].values()):
                raise RuntimeErrorUser("online_convertibility 必须是 YES/NO/UNKNOWN")
        elif kind == "information_requests":
            fields = {"question", "target_decision", "current_alternatives", "how_answer_changes_decision", "minimum_sample", "why_smaller_is_insufficient", "fallback_if_unavailable", "blocking"}
            missing = sorted(fields - set(record))
            if missing:
                raise RuntimeErrorUser(f"information request 缺少字段: {', '.join(missing)}")
            if not isinstance(record["blocking"], bool):
                raise RuntimeErrorUser("information_request.blocking 必须是布尔值")

    def touch_stage(self, stage: Any) -> None:
        if stage not in STAGES:
            return
        state = self.state()
        statuses = copy.deepcopy(state["stage_status"])
        if statuses[stage] == "NOT_STARTED":
            statuses[stage] = "IN_PROGRESS"
        self.write_state({"active_stage": stage, "stage_status": statuses})

    def set_objectives(self, objective_30d: dict[str, Any], forecast_90d: dict[str, Any]) -> dict[str, Any]:
        require(objective_30d, {"statement", "leading_indicators", "checkpoints"}, "objective_30d")
        require(forecast_90d, {"baseline", "upside", "risk", "triggers"}, "forecast_90d")
        state = self.write_state({"objective_30d": objective_30d, "forecast_90d": forecast_90d})
        self.handoff()
        return state

    def set_stage(self, stage: str, bottleneck: str, next_action: dict[str, Any], status: str) -> dict[str, Any]:
        if stage not in STAGES:
            raise RuntimeErrorUser("stage 必须是五阶段之一")
        if set(next_action) != NEXT_ACTION_FIELDS:
            missing = sorted(NEXT_ACTION_FIELDS - set(next_action))
            extra = sorted(set(next_action) - NEXT_ACTION_FIELDS)
            raise RuntimeErrorUser(f"next_action 字段错误；missing={missing} extra={extra}")
        if any(word in canonical(next_action) for word in FORBIDDEN_VAGUE):
            raise RuntimeErrorUser("next_action 包含不可复现词")
        state = self.state()
        statuses = copy.deepcopy(state["stage_status"])
        statuses[stage] = status
        result = self.write_state({"active_stage": stage, "current_bottleneck": bottleneck, "next_action": next_action, "stage_status": statuses})
        self.handoff()
        return result

    def node_records(self) -> dict[str, dict[str, Any]]:
        return {record["code"]: record for record in self.object_records("nodes")}

    def set_outcome(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create or revise the single current outcome contract."""
        payload = copy.deepcopy(payload)
        payload.setdefault("id", "OUTCOME-001")
        existing = next((item for item in self.object_records("outcomes") if item.get("id") == payload["id"]), None)
        result = self.add_object("outcomes", payload, replace=bool(existing))
        if existing and digest_value(without_hash(existing)) != digest_value(without_hash(result)):
            self.invalidate(["NODE-B0"], "结果合同发生语义变化")
        return result

    def set_node(self, code: str, payload: dict[str, Any]) -> dict[str, Any]:
        if code not in NODE_ORDER:
            raise RuntimeErrorUser(f"未知业务节点: {code}")
        current = self.node_records()[code]
        value = copy.deepcopy(current)
        value.update(copy.deepcopy(payload))
        value.update(
            {
                "node_id": f"NODE-{code}",
                "code": code,
                "name": NODE_NAMES[code],
                "business_stage": NODE_STAGE[code],
                "depends_on": [f"NODE-{item}" for item in NODE_DEPENDENCIES[code]],
            }
        )
        result = self.add_object("nodes", value, replace=True)
        semantic_fields = ("summary", "status", "evidence_refs", "alternative_ids", "counterevidence")
        changed = any(current.get(field) != result.get(field) for field in semantic_fields)
        if current.get("status") == "APPROVED" and changed:
            self.invalidate([f"NODE-{code}"], f"{code} 已批准结论被修订")
        current_node = self._earliest_open_node()
        self.write_state({"current_node": f"NODE-{current_node}", "active_stage": NODE_STAGE[current_node]})
        self.handoff()
        return result

    def add_alternative(self, payload: dict[str, Any], *, replace: bool = False) -> dict[str, Any]:
        return self.add_object("alternatives", payload, replace=replace)

    def add_information_request(self, payload: dict[str, Any], *, replace: bool = False) -> dict[str, Any]:
        return self.add_object("information_requests", payload, replace=replace)

    def _earliest_open_node(self) -> str:
        nodes = self.node_records()
        for code in NODE_ORDER:
            if nodes.get(code, {}).get("status") not in {"APPROVED", "SUPERSEDED"}:
                return code
        return "O1"

    def preflight(self, target: str) -> dict[str, Any]:
        code = target.removeprefix("NODE-")
        if code not in NODE_ORDER:
            raise RuntimeErrorUser(f"未知业务节点: {target}")
        nodes = self.node_records()
        dependencies = NODE_DEPENDENCIES[code]
        missing = []
        invalid = []
        unknown = []
        for dependency in dependencies:
            status = nodes[dependency]["status"]
            if status == "INVALIDATED":
                invalid.append(f"NODE-{dependency}")
            elif status not in {"APPROVED", "SUPERSEDED"}:
                unknown.append(f"NODE-{dependency}")
        blocking = sorted(set(missing + invalid + unknown))
        warnings = []
        if code == "B5":
            for precheck in ("B6", "B7"):
                candidate_ids = nodes[precheck].get("alternative_ids", [])
                if len(candidate_ids) < 2:
                    warnings.append({"code": "W-W3-W6-PRECHECK", "node": f"NODE-{precheck}", "message": "锁定 W1/W2 前需要至少两个 W3–W6 候选及最小反证"})
        return {
            "target": f"NODE-{code}",
            "dependencies": [f"NODE-{item}" for item in dependencies],
            "missing_dependency_ids": missing,
            "unknown_dependency_ids": unknown,
            "invalidated_dependency_ids": invalid,
            "blocking_dependency_ids": blocking,
            "warnings": warnings,
            "allowed": not blocking,
            "minimal_repairs": [f"先把 {identifier} 推进到 APPROVED，并保留证据、反证与审批溯源" for identifier in blocking],
        }

    @staticmethod
    def _issue(code: str, record_id: str, relation: str, message: str, repair: str) -> dict[str, str]:
        return {
            "code": code,
            "record_id": record_id,
            "violated_relation": relation,
            "message": message,
            "minimal_repair": repair,
        }

    def business_validate(self, records: dict[str, dict[str, Any]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        errors: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []
        nodes = self.node_records()
        outcomes = [item for item in self.object_records("outcomes") if not item.get("stale") and item.get("status") == "APPROVED"]
        high_impact_active = any(nodes[code]["status"] == "APPROVED" for code in ("B5", "B6", "B7", "C1", "C2", "P1", "O1"))
        if high_impact_active and not outcomes:
            errors.append(self._issue("E-OUTCOME-MISSING", "NODE-B0", "B0 -> B5..O1", "高影响定位或下游节点已批准，但没有批准的结果合同。", "先定义核心正价/等价价值交换成功事件、领先事件和排除事件。"))
        for outcome in outcomes:
            success = outcome.get("success_event", {})
            name = str(success.get("name", "")).strip().lower()
            leading = {str(item.get("name", "")).strip().lower() for item in outcome.get("leading_events", [])}
            excluded = {str(item).strip().lower() for item in outcome.get("excluded_success_events", [])}
            if name in leading or name in excluded or success.get("event_category") == "LEADING_EVENT" or not success.get("requires_full_price", False):
                errors.append(self._issue("E-OUTCOME-SUBSTITUTION", outcome["id"], "success_event != leading_event", "咨询、预约、到店、留资、检查或方案沟通不能替代批准的真实价值交换。", "把该事件移入 leading_events，并定义真实正价或等价价值交换事件。"))

        for code in NODE_ORDER:
            node = nodes[code]
            if node.get("status") != "APPROVED":
                continue
            for dependency in NODE_DEPENDENCIES[code]:
                if nodes[dependency].get("status") not in {"APPROVED", "SUPERSEDED"}:
                    errors.append(self._issue("E-NODE-DEPENDENCY", node["node_id"], f"NODE-{dependency} -> NODE-{code}", f"{code} 已批准，但依赖 {dependency} 尚未批准。", f"先推进 NODE-{dependency}，或把 NODE-{code} 降为 HYPOTHESIS。"))
        if any(nodes[code]["status"] == "APPROVED" for code in ("C1", "C2", "P1")) and nodes["B5"]["status"] != "APPROVED":
            errors.append(self._issue("E-CONTENT-BEFORE-AUDIENCE", "NODE-C1", "B5 -> C1/C2/P1", "目标人和阶段未批准，内容或生产却已批准。", "先完成 B5 的目标人、阶段、排除对象、替代方案和反证。"))
        if nodes["B5"]["status"] == "APPROVED" and nodes["B4"]["status"] != "APPROVED":
            errors.append(self._issue("E-ONLINE-CONVERTIBILITY-UNKNOWN", "NODE-B5", "B4 -> B5", "未分别判断可触达、可识别、可影响和可归因，就锁定了目标人。", "先完成 B4 四维线上可转化判断；不成立时换人群、阶段或渠道。"))
        if nodes["B5"]["status"] == "APPROVED":
            for code in ("B6", "B7"):
                if len(nodes[code].get("alternative_ids", [])) < 2:
                    errors.append(self._issue("E-PERSONA-BEFORE-W3-W6", "NODE-B5", f"{code} precheck -> B5", "锁定目标人前缺少 W3–W6 客户侧候选、反证和最小验证。", f"为 NODE-{code} 建立至少两个真实候选及最小否证测试。"))
        if nodes["B7"]["status"] in {"HYPOTHESIS", "NEEDS_EVIDENCE"} and len(nodes["B7"].get("alternative_ids", [])) >= 2:
            warnings.append(self._issue("W-W6-UNKNOWN", "NODE-B7", "W6 hypothesis", "最终付款理由尚未证实，但已有候选和最小验证，可继续探索。", "保持 HYPOTHESIS/NEEDS_EVIDENCE；不得升级为批准或把领先事件当付款。"))

        sources = {item["source_id"]: item for item in self.object_records("sources")}
        b5 = nodes["B5"]
        if b5.get("status") == "APPROVED" and b5.get("decision_scope", {}).get("locality") == "local":
            evidence_sources = [sources[item] for item in b5.get("evidence_refs", []) if item in sources]
            if evidence_sources and all(item.get("evidence_level") in {"E3_EXTERNAL_SAME_PATTERN", "E4_RESEARCH_ANALOG"} for item in evidence_sources):
                errors.append(self._issue("E-LOCAL-RANKING-BY-GENERAL-RESEARCH", "NODE-B5", "external evidence -> local ranking", "泛行业或外地研究只能生成候选，不能单独批准本地第一目标人。", "补一条能改变排序的 E1/E2 本地证据，或把排序降为待验证假设。"))

        for identifier, decision in self.ndjson_latest("decisions").items():
            if decision.get("stale") or decision.get("decision_type") != "PERSONA":
                continue
            test = decision.get("customer_side_test", {})
            required = ("passes_title_free", "customer_barrier", "perceivable_behavior", "why_not_any_peer", "disconfirming_signal")
            if not all(test.get(field) not in (None, "", "UNKNOWN") for field in required) or test.get("passes_title_free") is not True:
                errors.append(self._issue("E-PERSONA-INSIDE-OUT", identifier, "internal responsibility != customer purchase reason", "人物理由删除姓名和职务后无法说明客户障碍、可感知行为、独特性和反证。", "从客户当前障碍重写 title-free 理由，并登记可感知证据和否证信号。"))

        for request in self.object_records("information_requests"):
            if request.get("stale"):
                continue
            if not request.get("target_decision") or not request.get("how_answer_changes_decision"):
                errors.append(self._issue("E-DATA-REQUEST-NO-DECISION", request["request_id"], "information request -> decision", "信息请求没有说明会改变哪个决定。", "补 target_decision、当前候选和两种答案分别如何改变选择。"))
            sample = f"{request.get('question', '')} {request.get('minimum_sample', '')}".lower()
            oversized = any(token in sample for token in ("12个月", "6个月", "全部客户", "完整客户", "全量"))
            if oversized and not request.get("why_smaller_is_insufficient"):
                errors.append(self._issue("E-DATA-REQUEST-OVERSIZED", request["request_id"], "requested sample > minimum necessary", "索取超量资料但没有证明更小样本为何不足。", "先用现有资料和 2–3 个候选；将样本缩到能区分当前决定的最小范围。"))

        for identifier, approval in self.ndjson_latest("approvals").items():
            if approval.get("status") != "ACTIVE" or approval.get("stale"):
                continue
            quote = str(approval.get("user_quote", "")).strip()
            if quote in AMBIGUOUS_APPROVAL_QUOTES or not approval.get("source_turn_or_file") or not approval.get("interpreted_scope"):
                errors.append(self._issue("E-APPROVAL-NO-PROVENANCE", identifier, "user quote -> interpreted approval scope", "模糊肯定或缺少来源，不能扩大为方向、实验、成果或发布批准。", "保留用户原话、精确范围、明确排除和来源；不清楚时保持 NEEDS_RECONFIRMATION。"))
        active_direction_targets = {
            item.get("target_id")
            for item in self.ndjson_latest("approvals").values()
            if item.get("status") == "ACTIVE" and not item.get("stale") and item.get("approval_type") == "DIRECTION"
        }
        for code, node in nodes.items():
            if node.get("status") == "APPROVED" and node["node_id"] not in active_direction_targets:
                errors.append(self._issue("E-APPROVAL-NO-PROVENANCE", node["node_id"], "direction approval -> approved node", f"{code} 标为 APPROVED，但没有范围匹配、带原话的 DIRECTION 审批。", "将节点降为 NEEDS_APPROVAL，或登记精确 DIRECTION 审批。"))

        for identifier, claim in self.ndjson_latest("claims").items():
            scope = claim.get("scope", {})
            locality = scope.get("locality") if isinstance(scope, dict) else None
            if locality != "local" or claim.get("truth_status") in {"UNVERIFIED", "SUPPORTED_HYPOTHESIS"}:
                continue
            referenced = [sources[item] for item in claim.get("source_refs", []) if item in sources]
            if referenced and all(item.get("scope", {}).get("locality") in {"general", "external"} for item in referenced if isinstance(item.get("scope"), dict)):
                errors.append(self._issue("E-EVIDENCE-SCOPE-MISMATCH", identifier, "evidence scope >= conclusion scope", "证据适用范围小于本地事实结论范围。", "缩窄为候选假设，或补足同地域同对象证据。"))
            for conflict_id in claim.get("conflicts_with", []):
                other = self.ndjson_latest("claims").get(conflict_id)
                if not other:
                    continue
                pair = {claim.get("evidence_level"), other.get("evidence_level")}
                if pair & {"E1_LOCAL_EXACT", "E2_LOCAL_ADJACENT"} and pair & {"E3_EXTERNAL_SAME_PATTERN", "E4_RESEARCH_ANALOG"}:
                    warnings.append(self._issue("W-RESEARCH-CONFLICT", identifier, "external evidence <> local fact", "外部研究与本地一手事实冲突；不得自动覆盖本地事实。", "保留两条 claim 为 DISPUTED/待裁决，只请求能改变当前决策的最小本地证据。"))

        if outcomes:
            success_evidence = [item for item in outcomes[0].get("success_event", {}).get("evidence_required", []) if item]
            if not success_evidence:
                warnings.append(self._issue("W-LEADING-METRIC-ONLY", outcomes[0]["id"], "leading metrics without transaction evidence", "结果合同未声明交易验证证据。", "补充付款、合同或等价真实价值交换证据。"))
        return errors, warnings

    def validate(self, *, structural_only: bool = False) -> dict[str, Any]:
        self.ensure_initialized()
        structural_errors: list[str] = []
        state = self.state()
        if state.get("schema_version") != STATE_SCHEMA:
            structural_errors.append("project-state schema_version 不匹配")
        if state.get("runtime_version") != RUNTIME_VERSION:
            structural_errors.append("runtime_version 不匹配；先运行 migrate --to 4")
        if state.get("active_stage") not in STAGES:
            structural_errors.append("active_stage 不是五阶段")
        if state.get("current_node") not in {f"NODE-{code}" for code in NODE_ORDER}:
            structural_errors.append("current_node 不是 B0–O1 原子节点")
        if state.get("state_hash") != digest_value(without_hash(state)):
            structural_errors.append("project-state 哈希不匹配")
        if set(state.get("next_action", {})) != NEXT_ACTION_FIELDS:
            structural_errors.append("next_action 字段不完整")
        try:
            self.method_registry()
        except RuntimeErrorUser as error:
            structural_errors.append(str(error))
        try:
            self.invariant_registry()
        except RuntimeErrorUser as error:
            structural_errors.append(str(error))
        try:
            records = self.all_latest()
        except RuntimeErrorUser as error:
            records = {}
            structural_errors.append(str(error))
        for identifier, record in records.items():
            if record.get("payload_hash") != digest_value(without_hash(record)):
                structural_errors.append(f"{identifier} payload_hash 不匹配")
            for dependency in record.get("depends_on", []):
                if dependency not in records:
                    structural_errors.append(f"{identifier} 依赖不存在: {dependency}")
            for source_ref in record.get("source_refs", []) + record.get("sources", []):
                if source_ref not in records or not source_ref.startswith("SRC-"):
                    structural_errors.append(f"{identifier} 来源不存在: {source_ref}")
            for evidence_ref in record.get("evidence_refs", []):
                if evidence_ref not in records:
                    structural_errors.append(f"{identifier} 证据引用不存在: {evidence_ref}")
            for claim_ref in record.get("hypothesis_claim_ids", []) + record.get("target_claim_ids", []):
                if claim_ref not in records or not claim_ref.startswith("CLM-"):
                    structural_errors.append(f"{identifier} claim 引用不存在: {claim_ref}")
            if identifier.startswith("ART-"):
                relative = record.get("relative_path")
                if relative:
                    target = self.root / relative
                    if not target.is_file() or sha256_file(target) != record.get("content_sha256"):
                        structural_errors.append(f"{identifier} 成果内容不存在或哈希不匹配")
        registered_paths = {str(record.get("relative_path")) for identifier, record in records.items() if identifier.startswith("ART-") and record.get("relative_path")}
        artifacts_root = self.root / "artifacts"
        if artifacts_root.is_dir():
            for target in sorted(path for path in artifacts_root.rglob("*") if path.is_file() and not path.name.startswith(".")):
                relative = target.relative_to(self.root).as_posix()
                if relative not in registered_paths:
                    structural_errors.append(f"成果文件未登记: {relative}")
        for approval in self.ndjson_latest("approvals").values():
            target = approval.get("target_id")
            if target and target not in records:
                structural_errors.append(f"{approval['approval_id']} 目标不存在: {target}")
        business_errors: list[dict[str, str]] = []
        business_warnings: list[dict[str, str]] = []
        if not structural_only and not structural_errors:
            business_errors, business_warnings = self.business_validate(records)
        errors: list[Any] = list(structural_errors) + list(business_errors)
        return {
            "ok": not structural_errors and (structural_only or not business_errors),
            "structural_ok": not structural_errors,
            "business_ok": None if structural_only else not business_errors,
            "structural_only": structural_only,
            "structural_errors": structural_errors,
            "business_errors": business_errors,
            "business_warnings": business_warnings,
            "errors": errors,
            "project_id": state.get("project_id"),
            "active_stage": state.get("active_stage"),
            "current_node": state.get("current_node"),
            "records": len(records),
        }

    def status(self) -> dict[str, Any]:
        result = self.validate()
        if not result["ok"]:
            raise RuntimeErrorUser("项目校验失败: " + "; ".join(str(item) for item in result["errors"]))
        state = self.state()
        counts = {kind: len(self.ndjson_latest(kind)) for kind in NDJSON_FILES}
        counts.update({kind: len(self.object_records(kind)) for kind in OBJECT_FILES})
        effective_approvals = [record for record in self.ndjson_latest("approvals").values() if self.approval_effective(record)]
        legacy = self.legacy_scan()
        return {
            "project_id": state["project_id"],
            "project_name": state["project_name"],
            "runtime_version": state["runtime_version"],
            "active_stage": state["active_stage"],
            "current_node": state["current_node"],
            "node_status": {code: self.node_records()[code]["status"] for code in NODE_ORDER},
            "current_bottleneck": state["current_bottleneck"],
            "objective_30d": state["objective_30d"],
            "forecast_90d": state["forecast_90d"],
            "stage_status": state["stage_status"],
            "migration_status": state["migration_status"],
            "next_action": state["next_action"],
            "counts": counts,
            "effective_approval_types": dict(Counter(record["approval_type"] for record in effective_approvals)),
            "business_warnings": result["business_warnings"],
            "legacy_skill_warning": legacy,
        }

    def capabilities(self) -> dict[str, Any]:
        registry = self.method_registry()
        stage_map: dict[str, list[str]] = {stage: [] for stage in STAGES}
        for method in registry["methods"]:
            for stage in method["stages"]:
                stage_map[stage].append(method["method_id"])
        public_methods = [{key: value for key, value in method.items() if key != "source_lineage"} for method in registry["methods"]]
        return {
            "skill": "$jw",
            "version": RUNTIME_VERSION,
            "business_stages": list(STAGES),
            "stage_method_map": stage_map,
            "methods": public_methods,
            "qualification_counts": dict(Counter(item["classification"] for item in registry["items"])),
            "business_nodes": [{"code": code, "name": NODE_NAMES[code], "stage": NODE_STAGE[code], "dependencies": NODE_DEPENDENCIES[code]} for code in NODE_ORDER],
            "commands": ["doctor", "capabilities", "init", "set-outcome", "set-node", "add-alternative", "add-information-request", "preflight", "validate", "status", "handoff", "migrate", "invalidate", "reconcile-portfolio", "can-publish", "export-feedback"],
        }

    def doctor(self) -> dict[str, Any]:
        registry = self.method_registry()
        manifest_path = self.skill_dir / "BUNDLE_MANIFEST.json"
        manifest = load_json(manifest_path, {})
        errors: list[str] = []
        checked = 0
        if manifest.get("version") != RUNTIME_VERSION:
            errors.append("BUNDLE_MANIFEST 版本不匹配")
        for entry in manifest.get("files", []):
            path = self.skill_dir / entry.get("path", "")
            if not path.is_file():
                errors.append(f"缺少包文件: {entry.get('path')}")
                continue
            checked += 1
            if sha256_file(path) != entry.get("sha256") or path.stat().st_size != entry.get("bytes"):
                errors.append(f"包文件哈希或大小不匹配: {entry.get('path')}")
        discovery_roots = [self.skill_dir.parent, self.project_root / ".agents" / "skills", Path.home() / ".agents" / "skills"]
        legacy: list[str] = []
        jw_installations: list[str] = []
        for root in discovery_roots:
            if not root.is_dir():
                continue
            for path in root.glob("jw*"):
                if not path.is_dir():
                    continue
                if path.name == "jw":
                    jw_installations.append(str(path.resolve()))
                elif path.name.startswith("jw-"):
                    legacy.append(str(path.resolve()))
        return {
            "ok": not errors and not legacy,
            "skill": "$jw",
            "version": RUNTIME_VERSION,
            "schema": STATE_SCHEMA,
            "python": sys.version.split()[0],
            "skill_dir": str(self.skill_dir),
            "bundle_manifest": str(manifest_path),
            "checked_files": checked,
            "method_count": len(registry["methods"]),
            "qualification_item_count": len(registry["items"]),
            "jw_installations": sorted(set(jw_installations)),
            "legacy_skill_residue": sorted(set(legacy)),
            "errors": errors,
        }

    def approval_effective(self, record: dict[str, Any]) -> bool:
        return record.get("status") == "ACTIVE" and not record.get("stale", False) and not is_expired(record.get("scope", {}).get("valid_until"))

    def add_approval(self, payload: dict[str, Any], *, revise: bool = False) -> dict[str, Any]:
        payload = copy.deepcopy(payload)
        payload.setdefault("status", "ACTIVE")
        targets = self.all_latest()
        target = payload.get("target_id")
        if target not in targets:
            raise RuntimeErrorUser(f"审批目标不存在: {target}")
        approval_type = payload.get("approval_type")
        if approval_type == "EXPERIMENT" and not (target.startswith("EXP-") or target.startswith("NODE-")):
            raise RuntimeErrorUser("EXPERIMENT 只能指向实验或待验证节点")
        if approval_type == "ARTIFACT" and not target.startswith(("ART-", "CNT-")):
            raise RuntimeErrorUser("ARTIFACT 只能指向成果或内容")
        if approval_type == "PUBLISH" and not target.startswith(("ART-", "CNT-", "EXP-")):
            raise RuntimeErrorUser("PUBLISH 只能指向成果、内容或实验")
        if str(payload.get("user_quote", "")).strip() in AMBIGUOUS_APPROVAL_QUOTES and approval_type != "EXPERIMENT":
            payload["status"] = "NEEDS_RECONFIRMATION"
        return self.add_ndjson("approvals", payload, revise=revise)

    def register_artifact(self, payload: dict[str, Any], *, replace: bool = False) -> dict[str, Any]:
        payload = copy.deepcopy(payload)
        payload.setdefault("status", "ACTIVE")
        return self.add_object("artifacts", payload, replace=replace)

    def record_asset(self, content_id: str, artifact_id: str, status: str, units: float) -> dict[str, Any]:
        records = self.object_records("content")
        index = {record["content_id"]: position for position, record in enumerate(records)}
        if content_id not in index:
            raise RuntimeErrorUser(f"content 不存在: {content_id}")
        if artifact_id not in self.all_latest():
            raise RuntimeErrorUser(f"artifact 不存在: {artifact_id}")
        payload = copy.deepcopy(records[index[content_id]])
        payload["actual_units"] = float(payload.get("actual_units", 0)) + units
        refs = list(payload.get("artifact_refs", []))
        if artifact_id not in refs:
            refs.append(artifact_id)
        payload["artifact_refs"] = refs
        payload["status"] = status
        return self.add_object("content", payload, replace=True)

    def reconcile_portfolio(self) -> dict[str, Any]:
        contents = [record for record in self.object_records("content") if not record.get("stale")]
        planned_total = sum(float(record.get("planned_weight", 0)) for record in contents)
        actual_total = sum(float(record.get("actual_units", 0)) for record in contents)
        by_job: dict[str, dict[str, float]] = defaultdict(lambda: {"planned": 0.0, "actual": 0.0})
        rows = []
        for record in contents:
            planned_share = float(record.get("planned_weight", 0)) / planned_total if planned_total else 0.0
            actual_share = float(record.get("actual_units", 0)) / actual_total if actual_total else 0.0
            gap = actual_share - planned_share
            by_job[record["journey_job"]]["planned"] += planned_share
            by_job[record["journey_job"]]["actual"] += actual_share
            rows.append({"content_id": record["content_id"], "title": record["title"], "journey_job": record["journey_job"], "planned_share": round(planned_share, 4), "actual_share": round(actual_share, 4), "gap": round(gap, 4), "status": record["status"]})
        result = {
            "generated_at": utc_now(),
            "planned_total": planned_total,
            "actual_total": actual_total,
            "rows": rows,
            "journey_coverage": {key: {name: round(value, 4) for name, value in values.items()} for key, values in sorted(by_job.items())},
            "gaps": [row for row in rows if abs(row["gap"]) >= 0.1 or row["actual_share"] == 0],
        }
        relative = "artifacts/portfolio-reconciliation.json"
        write_json(self.root / relative, result)
        existing = next((record for record in self.object_records("artifacts") if record.get("relative_path") == relative), None)
        payload = {
            "artifact_id": existing.get("artifact_id") if existing else None,
            "relative_path": relative,
            "artifact_type": "PORTFOLIO_RECONCILIATION",
            "business_stage": "PORTFOLIO",
            "method_refs": ["conversion-journey", "belief-mindshare", "orchestration-control"],
            "evidence_refs": [claim for record in contents for claim in record.get("target_claim_ids", [])],
            "counterevidence": [],
            "depends_on": [record["content_id"] for record in contents],
            "upstream_impacts": [],
            "downstream_impacts": ["OPERATIONS"],
            "horizon_30d": "用实际素材库存修正未来30天发布与补拍安排",
            "horizon_90d": "观察内容角色长期失衡是否导致心智或转化断点",
            "approval_state": "UNAPPROVED",
            "privacy": "PROJECT_PRIVATE",
            "status": "ACTIVE",
        }
        self.register_artifact(payload, replace=bool(existing))
        return result

    def invalidate(self, root_ids: list[str], reason: str) -> dict[str, Any]:
        records = self.all_latest()
        missing = [identifier for identifier in root_ids if identifier not in records]
        if missing:
            raise RuntimeErrorUser(f"失效根不存在: {missing}")
        children: dict[str, set[str]] = defaultdict(set)
        for identifier, record in records.items():
            dependencies = set(record.get("depends_on", []))
            dependencies.update(record.get("derived_from", []))
            if identifier.startswith("APR-"):
                if record.get("target_id"):
                    dependencies.add(record["target_id"])
            for dependency in dependencies:
                children[dependency].add(identifier)
        affected: set[str] = set()
        queue = deque(root_ids)
        while queue:
            identifier = queue.popleft()
            if identifier in affected:
                continue
            affected.add(identifier)
            queue.extend(children.get(identifier, set()))
        stages: set[str] = set()
        for kind, (filename, id_field, _) in NDJSON_FILES.items():
            latest = self.ndjson_latest(kind)
            for identifier in sorted(affected & set(latest)):
                payload = copy.deepcopy(latest[identifier])
                payload["stale"] = True
                payload["stale_reason"] = reason
                if kind == "approvals":
                    payload["status"] = "NEEDS_RECONFIRMATION"
                stage = payload.get("business_stage")
                if stage in STAGES:
                    stages.add(stage)
                append_ndjson(self.root / filename, stamped_record(payload, identifier_field=id_field, prefix="REV", previous=latest[identifier]))
        for kind, (_, id_field, _) in OBJECT_FILES.items():
            object_records = self.object_records(kind)
            changed = False
            for position, record in enumerate(object_records):
                identifier = record[id_field]
                if identifier not in affected:
                    continue
                payload = copy.deepcopy(record)
                payload["stale"] = True
                payload["stale_reason"] = reason
                if kind == "nodes":
                    payload["status"] = "INVALIDATED"
                    payload["approval_state"] = "NEEDS_RECONFIRMATION"
                stage = payload.get("business_stage")
                if stage in STAGES:
                    stages.add(stage)
                object_records[position] = stamped_record(payload, identifier_field=id_field, prefix="REV", previous=record)
                changed = True
            if changed:
                self.write_object_records(kind, object_records)
        return_stage = min(stages, key=lambda item: STAGE_ORDER[item]) if stages else "POSITIONING"
        state = self.state()
        statuses = copy.deepcopy(state["stage_status"])
        for stage in STAGES[STAGE_ORDER[return_stage]:]:
            if statuses[stage] == "COMPLETED":
                statuses[stage] = "NEEDS_REVIEW"
        next_action = {
            "owner": "project_owner",
            "minimum_input": f"只复核失效根及其直接反证：{', '.join(root_ids)}",
            "timebox": "下一次项目会话",
            "artifact": "修订后的最早业务判断与局部影响清单",
            "decision_threshold": "确认保留、修订或否决每个失效根",
            "stop_rule": "不得继续使用任何 stale 后代",
            "expansion_condition": "只有直接证据无法区分候选时再补最小样本",
        }
        self.write_state({"active_stage": return_stage, "current_bottleneck": f"上游判断已失效：{reason}", "stage_status": statuses, "next_action": next_action})
        self.handoff()
        return {"affected_ids": sorted(affected), "return_stage": return_stage, "unaffected_count": len(records) - len(affected)}

    def can_publish(self, target_id: str, channel: str, audience: str, action: str, version: str) -> dict[str, Any]:
        if target_id not in self.all_latest():
            raise RuntimeErrorUser(f"发布目标不存在: {target_id}")
        matches = []
        for approval in self.ndjson_latest("approvals").values():
            if approval.get("approval_type") != "PUBLISH" or not self.approval_effective(approval):
                continue
            scope = approval.get("scope", {})
            if target_id != approval.get("target_id"):
                continue
            if scope.get("channel") not in {channel, "*"}:
                continue
            if scope.get("audience") not in {audience, "*"}:
                continue
            if scope.get("action") not in {action, "*"}:
                continue
            if version not in scope.get("version_refs", []) and "*" not in scope.get("version_refs", []):
                continue
            matches.append(approval["approval_id"])
        return {"allowed": bool(matches), "matching_approvals": matches, "execution_status": "APPROVAL_MATCHED_TOOL_STILL_REQUIRED" if matches else "NOT_EXECUTED_NO_MATCHING_PRODUCTION_APPROVAL"}

    def legacy_scan(self) -> dict[str, Any]:
        legacy = sorted(path.name for path in self.skill_dir.parent.glob("jw-*") if path.is_dir())
        return {"found": bool(legacy), "skills": legacy, "action": "提示用户按升级说明清理；运行时不会调用或删除" if legacy else "none"}

    def migrate(self, project_id: str | None, name: str | None, *, to_version: int = 4) -> dict[str, Any]:
        if to_version != 4:
            raise RuntimeErrorUser("当前运行时只支持迁移到 Schema v4")
        if not self.root.exists():
            raise RuntimeErrorUser("没有可迁移的 .jw-project")
        old_state = load_json(self.state_path, {})
        if old_state.get("runtime_version") == RUNTIME_VERSION and old_state.get("schema_version") == STATE_SCHEMA:
            return {"migrated": False, "reason": "already_v4", "state_hash": old_state.get("state_hash")}
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = self.project_root / f".jw-project-legacy-{timestamp}"
        if backup.exists():
            raise RuntimeErrorUser(f"备份目录已存在: {backup}")
        os.replace(self.root, backup)
        old_claims = read_ndjson(backup / "claims.ndjson")
        old_approvals = read_ndjson(backup / "approvals.ndjson")
        old_sources = load_json(backup / "source-registry.json", {"sources": []})
        self.initialize(project_id or old_state.get("project_id", "PRJ-MIGRATED"), name or old_state.get("project_name", "Migrated JW project"))
        imported_sources = 0
        imported_source_ids: set[str] = set()
        for old in old_sources.get("sources", []) if isinstance(old_sources, dict) else []:
            source_id = old.get("source_id")
            if not isinstance(source_id, str) or not source_id:
                continue
            payload = {
                "source_id": source_id,
                "source_type": old.get("source_type", "legacy"),
                "title": old.get("title", source_id),
                "observed_at": old.get("observed_at", "UNKNOWN"),
                "evidence_level": old.get("evidence_level") if old.get("evidence_level") in EVIDENCE_LEVELS else "E5_PROJECT_JUDGMENT",
                "privacy": old.get("privacy", "PROJECT_PRIVATE"),
                "scope": old.get("scope", {"migration": "legacy"}),
                "cannot_prove": old.get("cannot_prove", ["旧来源不能自动证明 v4 业务结论"]),
                "migration_origin_id": source_id,
            }
            self.add_object("sources", payload)
            imported_source_ids.add(source_id)
            imported_sources += 1
        if not imported_source_ids:
            fallback = self.add_object(
                "sources",
                {
                    "source_id": "SRC-LEGACY-MIGRATION",
                    "source_type": "legacy_runtime_backup",
                    "title": "旧项目只读备份",
                    "observed_at": timestamp,
                    "evidence_level": "E5_PROJECT_JUDGMENT",
                    "privacy": "PROJECT_PRIVATE",
                    "scope": {"backup": backup.name},
                    "cannot_prove": ["只读备份不能自动批准旧业务结论"],
                },
            )
            imported_source_ids.add(fallback["source_id"])
            imported_sources += 1
        imported_facts = 0
        for old in latest_by(old_claims, "claim_id").values():
            if old.get("truth_status") != "CONFIRMED_FACT":
                continue
            payload = {
                "statement": old.get("statement", "迁移事实"),
                "subject": old.get("subject", "legacy_project"),
                "truth_status": "CONFIRMED_FACT",
                "evidence_level": old.get("evidence_level") if old.get("evidence_level") in EVIDENCE_LEVELS else "E5_PROJECT_JUDGMENT",
                "source_refs": [source for source in old.get("source_refs", []) if source in imported_source_ids] or [sorted(imported_source_ids)[0]],
                "scope": old.get("scope", {"migration": "legacy"}),
                "time_validity": old.get("time_validity", "UNKNOWN"),
                "counterevidence": old.get("counterevidence", []),
                "confidence": old.get("confidence", 0.5),
                "derived_from": [],
                "migration_origin_id": old.get("claim_id"),
            }
            self.add_ndjson("claims", payload)
            imported_facts += 1
        leading_candidates: list[str] = []
        for old in latest_by(old_claims, "claim_id").values():
            statement = str(old.get("statement", ""))
            if any(token in statement for token in ("咨询", "预约", "到店", "留资", "检查", "方案沟通")) and any(token in statement for token in ("成功", "成交", "结果")):
                leading_candidates.append(statement)
        if leading_candidates:
            self.set_outcome(
                {
                    "id": "OUTCOME-LEGACY-001",
                    "version": 1,
                    "core_offer": {
                        "name": "旧项目核心产品待复核",
                        "scope": "NEEDS_REQUALIFICATION",
                        "price_basis": "待用户定义正价口径",
                        "capacity_constraints": [],
                        "material_exclusions": leading_candidates,
                    },
                    "success_event": {
                        "name": "真实价值交换待定义",
                        "definition": "旧项目没有可复用的 v4 成交定义",
                        "event_category": "VALUE_EXCHANGE",
                        "requires_full_price": True,
                        "evidence_required": ["用户重新确认的付款或等价价值交换证据"],
                        "attribution_window": "待确认",
                    },
                    "leading_events": [{"name": item, "purpose": "旧记录中的过程信号", "not_success_reason": "v4 不允许自动视为成交"} for item in leading_candidates],
                    "excluded_success_events": leading_candidates,
                    "economics": {
                        "minimum_viable_margin_basis": "待确认",
                        "capacity_basis": "待确认",
                        "repeatability_basis": "待确认",
                    },
                    "status": "HYPOTHESIS",
                    "sources": [sorted(imported_source_ids)[0]],
                    "approved_by": None,
                    "approved_at": None,
                    "migration_semantic_downgrade": "旧领先事件不再视为成功事件",
                }
            )
        imported_approvals = 0
        for old in latest_by(old_approvals, "approval_id").values():
            historical = {
                "target_id": "NODE-B0",
                "approval_type": "DIRECTION",
                "user_quote": old.get("user_quote", "[旧审批缺少用户原话]"),
                "interpreted_scope": canonical(redact(old.get("scope", {}))),
                "explicit_exclusions": ["不自动批准 v4 结果合同、节点、成果或发布"],
                "assumptions_acknowledged": ["旧审批语义未满足 v4 溯源要求"],
                "source_turn_or_file": old.get("source_turn_or_file", backup.name),
                "scope": {"historical_scope": redact(old.get("scope", {})), "migration_origin_id": old.get("approval_id")},
                "status": "NEEDS_RECONFIRMATION",
            }
            self.add_ndjson("approvals", historical)
            imported_approvals += 1
        self.write_state({"migration_status": "NEEDS_REQUALIFICATION", "legacy_backup": backup.name, "active_stage": "POSITIONING", "current_node": "NODE-B0", "current_bottleneck": "旧业务结论需要按 B0–O1 重新资格审查"})
        report = {
            "schema_version": "jw.migration-report.v4",
            "generated_at": utc_now(),
            "source_schema": old_state.get("schema_version"),
            "target_schema": STATE_SCHEMA,
            "backup": backup.name,
            "automatic_mappings": {"sources": imported_sources, "confirmed_facts": imported_facts},
            "semantic_downgrades": {
                "historical_approvals": imported_approvals,
                "leading_success_claims": leading_candidates,
                "old_business_conclusions": "NEEDS_REQUALIFICATION",
            },
            "unmapped": ["旧内容、人物路线、脚本、生产和运营结论"],
            "user_confirmations_required": ["B0 结果合同", "旧审批原话与范围", "B1–O1 业务节点"],
            "rollback": f"运行 `rollback-migration`：恢复 {backup.name}，并把当前 v4 状态移入隔离快照",
        }
        write_json(self.root / "migration-report.json", report)
        for path in sorted(backup.rglob("*"), reverse=True):
            try:
                path.chmod(0o555 if path.is_dir() else 0o444)
            except OSError:
                pass
        self.handoff()
        state = self.state()
        return {"migrated": True, "backup": str(backup), "imported_facts": imported_facts, "imported_sources": imported_sources, "historical_approvals": imported_approvals, "leading_success_downgrades": len(leading_candidates), "business_conclusions": "NEEDS_REQUALIFICATION", "state_revision": state.get("revision")}

    def rollback_migration(self) -> dict[str, Any]:
        if not self.root.exists():
            raise RuntimeErrorUser("没有可回滚的 .jw-project")
        state = load_json(self.state_path, {})
        backup_name = state.get("legacy_backup")
        if not isinstance(backup_name, str) or not backup_name:
            raise RuntimeErrorUser("当前项目没有可验证的 v3 迁移备份")
        backup = self.project_root / backup_name
        if not backup.is_dir():
            raise RuntimeErrorUser(f"迁移备份不存在: {backup}")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        quarantine = self.project_root / f".jw-project-v4-rollback-{timestamp}"
        if quarantine.exists():
            raise RuntimeErrorUser(f"回滚隔离目录已存在: {quarantine}")
        os.replace(self.root, quarantine)
        try:
            os.replace(backup, self.root)
        except Exception:
            os.replace(quarantine, self.root)
            raise
        for path in sorted(self.root.rglob("*")):
            try:
                path.chmod(0o755 if path.is_dir() else 0o644)
            except OSError:
                pass
        try:
            self.root.chmod(0o755)
        except OSError:
            pass
        return {
            "rolled_back": True,
            "restored_schema": load_json(self.state_path, {}).get("schema_version"),
            "restored_project": str(self.root),
            "v4_quarantine": str(quarantine),
            "data_deleted": False,
        }

    def handoff(self) -> Path:
        state = self.state()
        claims = self.ndjson_latest("claims")
        decisions = self.ndjson_latest("decisions")
        approvals = self.ndjson_latest("approvals")
        active_claims = [record for record in claims.values() if not record.get("stale")]
        active_decisions = [record for record in decisions.values() if not record.get("stale")]
        effective_approvals = [record for record in approvals.values() if self.approval_effective(record)]
        outcomes = [item for item in self.object_records("outcomes") if not item.get("stale")]
        nodes = self.node_records()
        validation = self.validate()
        next_action = state["next_action"]
        lines = [
            f"# HANDOFF — {state['project_name']}",
            "",
            f"- Runtime: `{state['runtime_version']}`",
            f"- Active business stage: `{state['active_stage']}`",
            f"- Current atomic node: `{state['current_node']}`",
            f"- Current bottleneck: {state['current_bottleneck']}",
            f"- Migration: `{state['migration_status']}`",
            "",
            "## Approved outcome contract",
            "",
        ]
        approved_outcomes = [item for item in outcomes if item.get("status") == "APPROVED"]
        if approved_outcomes:
            outcome = approved_outcomes[-1]
            lines.extend(
                [
                    f"- Offer: {outcome['core_offer'].get('name')}",
                    f"- Success event: {outcome['success_event'].get('name')}",
                    f"- Definition: {outcome['success_event'].get('definition')}",
                    f"- Attribution window: {outcome['success_event'].get('attribution_window')}",
                    f"- Leading events are not success: {', '.join(str(item.get('name')) for item in outcome.get('leading_events', [])) or 'none'}",
                ]
            )
        else:
            lines.append("- No approved outcome contract. B0 remains the controlling bottleneck.")
        lines.extend(
            [
                "",
                "## B0–O1 node state",
                "",
                "| Node | Meaning | Status | Summary |",
                "| --- | --- | --- | --- |",
            ]
        )
        for code in NODE_ORDER:
            node = nodes[code]
            lines.append(f"| {code} | {NODE_NAMES[code]} | `{node['status']}` | {str(node.get('summary', ''))[:160]} |")
        lines.extend(["", "## Five current business conclusions", ""])
        top = [item for item in active_decisions if item.get("status") == "ACTIVE"][-5:]
        if not top:
            lines.append("- None approved or active yet.")
        for decision in top:
            lines.extend(
                [
                    f"### {decision['decision_id']}",
                    "",
                    f"- Conclusion: {decision.get('statement')}",
                    f"- Evidence: {', '.join(decision.get('evidence_refs', [])) or 'none'}",
                    f"- Counterevidence: {canonical(decision.get('counterevidence', []))}",
                    f"- Invalidated by: {canonical(decision.get('invalidation_conditions', ['new contradictory evidence']))}",
                    "",
                ]
            )
        rejected = [item for item in active_decisions if item.get("status") == "REJECTED"]
        lines.extend(["## Explicitly rejected paths", ""])
        lines.extend([f"- {item.get('statement')} — {item.get('rationale_summary', '')}" for item in rejected] or ["- None recorded."])
        earliest = self._earliest_open_node()
        lines.extend(
            [
                "",
                "## Largest current business unknown",
                "",
                f"- `{earliest}` {NODE_NAMES[earliest]}: {nodes[earliest].get('summary', '待判断')}",
                "",
                "## Unique next action",
                "",
            ]
        )
        for field in ("owner", "minimum_input", "timebox", "artifact", "decision_threshold", "stop_rule", "expansion_condition"):
            lines.append(f"- {field}: {next_action[field]}")
        affected = sorted({item for record in active_decisions for item in record.get("downstream_impacts", [])})
        pending_approvals = [record for record in approvals.values() if record.get("status") in {"NEEDS_RECONFIRMATION"}]
        lines.extend(
            [
                "",
                "## Downstream impact",
                "",
                f"- Potentially affected: {', '.join(affected) or 'none'}",
                "",
                "## Pending approvals",
                "",
            ]
        )
        lines.extend([f"- {item['approval_id']}: {item.get('target_id')} needs reconfirmation" for item in pending_approvals] or ["- None."])
        lines.extend(
            [
                "",
                "## Validation",
                "",
                f"- Structural: `{'PASS' if validation['structural_ok'] else 'FAIL'}`",
                f"- Business: `{'PASS' if validation['business_ok'] else 'FAIL'}`",
                f"- Business errors: {', '.join(item['code'] for item in validation['business_errors']) or 'none'}",
                f"- Business warnings: {', '.join(item['code'] for item in validation['business_warnings']) or 'none'}",
                "",
                "## 30-day and 90-day horizon",
                "",
                f"- 30-day: {state['objective_30d'].get('statement', '待确定')}",
                f"- 90-day baseline: {state['forecast_90d'].get('baseline', '待确定')}",
                f"- 90-day upside: {state['forecast_90d'].get('upside', '待确定')}",
                f"- 90-day risk: {state['forecast_90d'].get('risk', '待确定')}",
                "",
                "## Safety",
                "",
                "No external production, publishing, outreach or media spend without a matching `PUBLISH` approval and an available execution tool.",
                "",
            ]
        )
        target = self.root / "HANDOFF_LATEST.md"
        atomic_write(target, "\n".join(lines))
        return target

    def export_feedback(self) -> dict[str, Any]:
        self.status()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        export_dir = self.root / "exports" / f"jw-feedback-{timestamp}"
        export_dir.mkdir(parents=True, exist_ok=False)
        state = redact(self.state())
        latest_feedback = list(self.ndjson_latest("feedback").values())
        summary = {
            "schema_version": "jw.feedback-export.v1",
            "generated_at": utc_now(),
            "project": {"project_id": state["project_id"], "project_name": state["project_name"], "active_stage": state["active_stage"], "current_bottleneck": state["current_bottleneck"], "objective_30d": state["objective_30d"], "forecast_90d": state["forecast_90d"]},
            "feedback": redact(latest_feedback),
            "content_inventory": redact(self.object_records("content")),
            "artifact_registry": redact(self.object_records("artifacts")),
            "record_counts": self.status()["counts"],
            "excluded": ["sources/ raw files", "artifacts/ contents", "contact fields", "raw conversations", "customer identifiers"],
        }
        write_json(export_dir / "feedback-summary.json", summary)
        corrections = sum(len(item.get("user_corrections", [])) for item in latest_feedback)
        repeated = sum(len(item.get("repeated_questions", [])) for item in latest_feedback)
        markdown = [
            "# JW v4.0.0-rc.1 实测反馈",
            "",
            f"- 项目：{redact(state['project_name'])}",
            f"- 当前阶段：{state['active_stage']}",
            f"- 用户纠正：{corrections}",
            f"- 重复提问：{repeated}",
            f"- 当前瓶颈：{redact(state['current_bottleneck'])}",
            "",
            "本包不包含原始客户资料、聊天全文、联系方式或成果正文。详细结构化反馈见 `feedback-summary.json`。",
            "",
        ]
        atomic_write(export_dir / "TEST_FEEDBACK.md", "\n".join(markdown))
        shutil.copy2(self.root / "HANDOFF_LATEST.md", export_dir / "HANDOFF_LATEST.md")
        archive = self.root / "exports" / f"jw-feedback-{timestamp}.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as handle:
            for path in sorted(export_dir.rglob("*")):
                if path.is_file():
                    handle.write(path, path.relative_to(export_dir.parent).as_posix())
        return {"archive": str(archive), "sha256": sha256_file(archive), "files": sorted(path.name for path in export_dir.iterdir())}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="线索获客4.0 v4.0.0-rc.1 业务推理与项目控制运行时")
    sub = parser.add_subparsers(dest="command", required=True)

    def project_command(name: str, help_text: str) -> argparse.ArgumentParser:
        command = sub.add_parser(name, help=help_text)
        command.add_argument("project")
        return command

    init = project_command("init", "初始化项目")
    init.add_argument("--project-id", required=True)
    init.add_argument("--name", required=True)
    validate = project_command("validate", "同时校验结构和业务语义")
    validate.add_argument("--structural-only", action="store_true", help="仅用于迁移和维修，不得作为发行验收")
    project_command("status", "读取当前状态")
    project_command("doctor", "检查 Skill 版本、完整性、旧版残留和运行环境")
    project_command("capabilities", "显示五阶段、七方法和调用关系")
    project_command("handoff", "生成交接")
    project_command("legacy-scan", "检测旧 Skill")
    migrate = project_command("migrate", "迁移旧项目")
    migrate.add_argument("--project-id")
    migrate.add_argument("--name")
    migrate.add_argument("--to", type=int, default=4, choices=(4,))
    project_command("rollback-migration", "非破坏式恢复迁移前项目，并隔离当前 v4 状态")

    outcome = project_command("set-outcome", "设置结果合同")
    outcome.add_argument("--json", required=True)
    node = project_command("set-node", "设置 B0–O1 原子节点")
    node.add_argument("--node", choices=NODE_ORDER, required=True)
    node.add_argument("--json", required=True)
    alternative = project_command("add-alternative", "登记结构化替代方案")
    alternative.add_argument("--json", required=True)
    alternative.add_argument("--replace", action="store_true")
    information = project_command("add-information-request", "登记最小信息请求")
    information.add_argument("--json", required=True)
    information.add_argument("--replace", action="store_true")
    preflight = project_command("preflight", "检查目标节点依赖、阻断和最小修复")
    preflight.add_argument("--target", required=True)

    objectives = project_command("set-objectives", "设置30天目标与90天预测")
    objectives.add_argument("--objective-30d-json", required=True)
    objectives.add_argument("--forecast-90d-json", required=True)
    stage = project_command("set-stage", "设置当前阶段和下一步")
    stage.add_argument("--stage", choices=STAGES, required=True)
    stage.add_argument("--bottleneck", required=True)
    stage.add_argument("--next-action-json", required=True)
    stage.add_argument("--status", choices=("NOT_STARTED", "IN_PROGRESS", "READY", "COMPLETED", "NEEDS_REVIEW", "BLOCKED"), default="IN_PROGRESS")

    for command_name, kind in (("add-source", "sources"), ("add-entity", "entities"), ("add-claim", "claims"), ("add-decision", "decisions"), ("add-experiment", "experiments"), ("record-feedback", "feedback"), ("add-content", "content")):
        command = project_command(command_name, command_name)
        command.add_argument("--json", required=True)
        if kind in NDJSON_FILES:
            command.add_argument("--revise", action="store_true")
        else:
            command.add_argument("--replace", action="store_true")
        command.set_defaults(record_kind=kind)
    approval = project_command("add-approval", "登记审批")
    approval.add_argument("--json", required=True)
    approval.add_argument("--revise", action="store_true")
    artifact = project_command("register-artifact", "登记成果")
    artifact.add_argument("--json", required=True)
    artifact.add_argument("--replace", action="store_true")
    asset = project_command("record-asset", "登记实际素材")
    asset.add_argument("--content-id", required=True)
    asset.add_argument("--artifact-id", required=True)
    asset.add_argument("--status", choices=("SHOT", "EDITED", "READY", "PUBLISHED", "OBSERVED"), required=True)
    asset.add_argument("--units", type=float, default=1.0)
    project_command("reconcile-portfolio", "对账内容组合")
    invalidate = project_command("invalidate", "局部失效传播")
    invalidate.add_argument("--root-id", action="append", required=True)
    invalidate.add_argument("--reason", required=True)
    publish = project_command("can-publish", "核验生产批准")
    publish.add_argument("--target-id", required=True)
    publish.add_argument("--channel", required=True)
    publish.add_argument("--audience", required=True)
    publish.add_argument("--action", required=True)
    publish.add_argument("--version", required=True)
    project_command("export-feedback", "导出脱敏反馈包")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    runtime = ProjectRuntime(args.project)
    try:
        if args.command == "init":
            result = runtime.initialize(args.project_id, args.name)
        elif args.command == "validate":
            result = runtime.validate(structural_only=args.structural_only)
        elif args.command == "status":
            result = runtime.status()
        elif args.command == "doctor":
            result = runtime.doctor()
        elif args.command == "capabilities":
            result = runtime.capabilities()
        elif args.command == "handoff":
            result = {"handoff": str(runtime.handoff())}
        elif args.command == "legacy-scan":
            result = runtime.legacy_scan()
        elif args.command == "migrate":
            result = runtime.migrate(args.project_id, args.name, to_version=args.to)
        elif args.command == "rollback-migration":
            result = runtime.rollback_migration()
        elif args.command == "set-outcome":
            result = runtime.set_outcome(parse_json_argument(args.json))
        elif args.command == "set-node":
            result = runtime.set_node(args.node, parse_json_argument(args.json))
        elif args.command == "add-alternative":
            result = runtime.add_alternative(parse_json_argument(args.json), replace=args.replace)
        elif args.command == "add-information-request":
            result = runtime.add_information_request(parse_json_argument(args.json), replace=args.replace)
        elif args.command == "preflight":
            result = runtime.preflight(args.target)
        elif args.command == "set-objectives":
            result = runtime.set_objectives(parse_json_argument(args.objective_30d_json), parse_json_argument(args.forecast_90d_json))
        elif args.command == "set-stage":
            result = runtime.set_stage(args.stage, args.bottleneck, parse_json_argument(args.next_action_json), args.status)
        elif hasattr(args, "record_kind"):
            payload = parse_json_argument(args.json)
            if args.record_kind in NDJSON_FILES:
                result = runtime.add_ndjson(args.record_kind, payload, revise=args.revise)
            else:
                result = runtime.add_object(args.record_kind, payload, replace=args.replace)
        elif args.command == "add-approval":
            result = runtime.add_approval(parse_json_argument(args.json), revise=args.revise)
        elif args.command == "register-artifact":
            result = runtime.register_artifact(parse_json_argument(args.json), replace=args.replace)
        elif args.command == "record-asset":
            result = runtime.record_asset(args.content_id, args.artifact_id, args.status, args.units)
        elif args.command == "reconcile-portfolio":
            result = runtime.reconcile_portfolio()
        elif args.command == "invalidate":
            result = runtime.invalidate(args.root_id, args.reason)
        elif args.command == "can-publish":
            result = runtime.can_publish(args.target_id, args.channel, args.audience, args.action, args.version)
        elif args.command == "export-feedback":
            result = runtime.export_feedback()
        else:
            raise RuntimeErrorUser("未知命令")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.command in {"validate", "doctor"} and not result.get("ok"):
            return 2
        return 0
    except RuntimeErrorUser as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
