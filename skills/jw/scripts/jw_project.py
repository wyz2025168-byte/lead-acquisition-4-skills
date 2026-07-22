#!/usr/bin/env python3
"""Deterministic local runtime for the public $jw business operating system."""

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


RUNTIME_VERSION = "3.0.0"
STATE_SCHEMA = "jw.project-state.v3"
REGISTRY_SCHEMA = "3.0.0"
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
APPROVAL_TYPES = {
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
}
FORBIDDEN_VAGUE = ("若干", "足量", "适当", "尽量")
DECISION_STATUSES = {"ACTIVE", "REJECTED", "NEEDS_REQUALIFICATION", "SUPERSEDED"}
APPROVAL_STATES = {"UNAPPROVED", "FACT_CONFIRMED", "HYPOTHESIS_ACCEPTED", "EXPERIMENT_AUTHORIZED", "PRODUCTION_APPROVED", "NEEDS_REQUALIFICATION"}


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
            "minimum_input": "提供现有产品、客户、交易、内容或运营资料；无需预先整理",
            "timebox": "首次接管会话",
            "artifact": "项目事实与最早业务瓶颈摘要",
            "decision_threshold": "能够区分至少两个业务解释并确定最早瓶颈",
            "stop_rule": "出现隐私、权限、合规或关键事实冲突时停止下传",
            "expansion_condition": "只有现有资料无法区分候选时再索取最小补充",
        }
        state = {
            "schema_version": STATE_SCHEMA,
            "runtime_version": RUNTIME_VERSION,
            "project_id": project_id,
            "project_name": name,
            "active_stage": "POSITIONING",
            "current_bottleneck": "等待读取项目资料并识别最早业务瓶颈",
            "objective_30d": {"statement": "待确定", "leading_indicators": [], "checkpoints": []},
            "forecast_90d": {"baseline": "待确定", "upside": "待确定", "risk": "待确定", "triggers": []},
            "stage_status": {stage: "NOT_STARTED" for stage in STAGES},
            "migration_status": "FRESH_V3",
            "next_action": initial_next,
            "created_at": now,
            "updated_at": now,
            "revision": 0,
        }
        state = stamped_state(state)
        write_json(self.state_path, state)
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
            require(record, {"approval_type", "approved_by", "scope", "status"}, "approval")
            if "target_ids" not in record or not isinstance(record["target_ids"], list):
                raise RuntimeErrorUser("approval.target_ids 必须是数组")
            if record["status"] == "ACTIVE" and not record["target_ids"]:
                raise RuntimeErrorUser("有效审批必须包含 target_ids")
            if record["approval_type"] not in APPROVAL_TYPES:
                raise RuntimeErrorUser("无效 approval_type")
            if record["status"] not in {"ACTIVE", "REVOKED", "NEEDS_REQUALIFICATION", "EXPIRED"}:
                raise RuntimeErrorUser("无效 approval status")
            if record["approval_type"] == "PRODUCTION_APPROVED" and record["status"] == "ACTIVE":
                require(record["scope"], {"channel", "audience", "action", "valid_until", "version_refs"}, "生产批准 scope")
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

    def validate(self) -> dict[str, Any]:
        self.ensure_initialized()
        errors: list[str] = []
        state = self.state()
        if state.get("schema_version") != STATE_SCHEMA:
            errors.append("project-state schema_version 不匹配")
        if state.get("runtime_version") != RUNTIME_VERSION:
            errors.append("runtime_version 不匹配；先运行 migrate")
        if state.get("active_stage") not in STAGES:
            errors.append("active_stage 不是五阶段")
        if state.get("state_hash") != digest_value(without_hash(state)):
            errors.append("project-state 哈希不匹配")
        if set(state.get("next_action", {})) != NEXT_ACTION_FIELDS:
            errors.append("next_action 字段不完整")
        try:
            self.method_registry()
        except RuntimeErrorUser as error:
            errors.append(str(error))
        try:
            records = self.all_latest()
        except RuntimeErrorUser as error:
            records = {}
            errors.append(str(error))
        for identifier, record in records.items():
            if record.get("payload_hash") != digest_value(without_hash(record)):
                errors.append(f"{identifier} payload_hash 不匹配")
            for dependency in record.get("depends_on", []):
                if dependency not in records:
                    errors.append(f"{identifier} 依赖不存在: {dependency}")
            for source_ref in record.get("source_refs", []):
                if source_ref not in records or not source_ref.startswith("SRC-"):
                    errors.append(f"{identifier} 来源不存在: {source_ref}")
            for evidence_ref in record.get("evidence_refs", []):
                if evidence_ref not in records:
                    errors.append(f"{identifier} 证据引用不存在: {evidence_ref}")
            for claim_ref in record.get("hypothesis_claim_ids", []) + record.get("target_claim_ids", []):
                if claim_ref not in records or not claim_ref.startswith("CLM-"):
                    errors.append(f"{identifier} claim 引用不存在: {claim_ref}")
            if identifier.startswith("ART-"):
                relative = record.get("relative_path")
                if relative:
                    target = self.root / relative
                    if not target.is_file() or sha256_file(target) != record.get("content_sha256"):
                        errors.append(f"{identifier} 成果内容不存在或哈希不匹配")
        registered_paths = {
            str(record.get("relative_path"))
            for identifier, record in records.items()
            if identifier.startswith("ART-") and record.get("relative_path")
        }
        artifacts_root = self.root / "artifacts"
        if artifacts_root.is_dir():
            for target in sorted(path for path in artifacts_root.rglob("*") if path.is_file() and not path.name.startswith(".")):
                relative = target.relative_to(self.root).as_posix()
                if relative not in registered_paths:
                    errors.append(f"成果文件未登记: {relative}")
        for approval in self.ndjson_latest("approvals").values():
            for target in approval.get("target_ids", []):
                if target not in records:
                    errors.append(f"{approval['approval_id']} 目标不存在: {target}")
        return {"ok": not errors, "errors": errors, "project_id": state.get("project_id"), "active_stage": state.get("active_stage"), "records": len(records)}

    def status(self) -> dict[str, Any]:
        result = self.validate()
        if not result["ok"]:
            raise RuntimeErrorUser("项目校验失败: " + "; ".join(result["errors"]))
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
            "current_bottleneck": state["current_bottleneck"],
            "objective_30d": state["objective_30d"],
            "forecast_90d": state["forecast_90d"],
            "stage_status": state["stage_status"],
            "migration_status": state["migration_status"],
            "next_action": state["next_action"],
            "counts": counts,
            "effective_approval_types": dict(Counter(record["approval_type"] for record in effective_approvals)),
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
            "commands": ["doctor", "capabilities", "init", "validate", "status", "handoff", "migrate", "invalidate", "reconcile-portfolio", "can-publish", "export-feedback"],
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
        for target in payload.get("target_ids", []):
            if target not in targets:
                raise RuntimeErrorUser(f"审批目标不存在: {target}")
        approval_type = payload.get("approval_type")
        for target in payload.get("target_ids", []):
            record = targets[target]
            if approval_type == "FACT_CONFIRMED" and record.get("truth_status") != "CONFIRMED_FACT":
                raise RuntimeErrorUser("FACT_CONFIRMED 只能指向 CONFIRMED_FACT")
            if approval_type == "HYPOTHESIS_ACCEPTED" and record.get("truth_status") not in {"SUPPORTED_HYPOTHESIS", "UNVERIFIED"}:
                raise RuntimeErrorUser("HYPOTHESIS_ACCEPTED 只能指向假设")
            if approval_type == "EXPERIMENT_AUTHORIZED" and not target.startswith("EXP-"):
                raise RuntimeErrorUser("EXPERIMENT_AUTHORIZED 只能指向实验")
            if approval_type == "PRODUCTION_APPROVED" and not target.startswith(("ART-", "CNT-", "EXP-")):
                raise RuntimeErrorUser("PRODUCTION_APPROVED 只能指向成果、内容或实验")
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
                dependencies.update(record.get("target_ids", []))
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
                    payload["status"] = "REVOKED"
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
            if approval.get("approval_type") != "PRODUCTION_APPROVED" or not self.approval_effective(approval):
                continue
            scope = approval.get("scope", {})
            if target_id not in approval.get("target_ids", []):
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

    def migrate(self, project_id: str | None, name: str | None) -> dict[str, Any]:
        if not self.root.exists():
            raise RuntimeErrorUser("没有可迁移的 .jw-project")
        old_state = load_json(self.state_path, {})
        if old_state.get("runtime_version") == RUNTIME_VERSION and old_state.get("schema_version") == STATE_SCHEMA:
            return {"migrated": False, "reason": "already_v3.0.0"}
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
        imported_approvals = 0
        for old in latest_by(old_approvals, "approval_id").values():
            historical = {
                "approval_type": old.get("approval_type") if old.get("approval_type") in APPROVAL_TYPES else "HYPOTHESIS_ACCEPTED",
                "target_ids": [],
                "approved_by": old.get("approved_by", "legacy_user"),
                "scope": {"historical_scope": redact(old.get("scope", {})), "migration_origin_id": old.get("approval_id")},
                "status": "NEEDS_REQUALIFICATION",
            }
            self.add_ndjson("approvals", historical)
            imported_approvals += 1
        state = self.state()
        self.write_state({"migration_status": "NEEDS_REQUALIFICATION", "legacy_backup": backup.name, "active_stage": "POSITIONING", "current_bottleneck": "旧业务结论需要按五阶段重新资格审查"})
        for path in sorted(backup.rglob("*"), reverse=True):
            try:
                path.chmod(0o555 if path.is_dir() else 0o444)
            except OSError:
                pass
        self.handoff()
        return {"migrated": True, "backup": str(backup), "imported_facts": imported_facts, "imported_sources": imported_sources, "historical_approvals": imported_approvals, "business_conclusions": "NEEDS_REQUALIFICATION", "state_revision": state.get("revision")}

    def handoff(self) -> Path:
        state = self.state()
        claims = self.ndjson_latest("claims")
        decisions = self.ndjson_latest("decisions")
        approvals = self.ndjson_latest("approvals")
        contents = self.object_records("content")
        active_claims = [record for record in claims.values() if not record.get("stale")]
        active_decisions = [record for record in decisions.values() if not record.get("stale")]
        effective_approvals = [record for record in approvals.values() if self.approval_effective(record)]
        next_action = state["next_action"]
        lines = [
            f"# HANDOFF — {state['project_name']}",
            "",
            f"- Runtime: `{state['runtime_version']}`",
            f"- Active business stage: `{state['active_stage']}`",
            f"- Current bottleneck: {state['current_bottleneck']}",
            f"- Migration: `{state['migration_status']}`",
            "",
            "## 30-day objective",
            "",
            str(state["objective_30d"].get("statement", "待确定")),
            "",
            "## 90-day forecast",
            "",
            f"- Baseline: {state['forecast_90d'].get('baseline', '待确定')}",
            f"- Upside: {state['forecast_90d'].get('upside', '待确定')}",
            f"- Risk: {state['forecast_90d'].get('risk', '待确定')}",
            "",
            "## Effective state",
            "",
            f"- Active claims: {len(active_claims)} / total {len(claims)}",
            f"- Active decisions: {len(active_decisions)} / total {len(decisions)}",
            f"- Effective approvals: {len(effective_approvals)} / total {len(approvals)}",
            f"- Content plans: {len(contents)}; actual units: {sum(float(item.get('actual_units', 0)) for item in contents)}",
            "",
            "## Unique next action",
            "",
        ]
        for field in ("owner", "minimum_input", "timebox", "artifact", "decision_threshold", "stop_rule", "expansion_condition"):
            lines.append(f"- {field}: {next_action[field]}")
        lines.extend(["", "## Safety", "", "No external production, publishing, outreach or media spend without a matching `PRODUCTION_APPROVED` and an available execution tool.", ""])
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
            "# JW v3.0.0 实测反馈",
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
    parser = argparse.ArgumentParser(description="线索获客4.0 v3.0.0 项目运行时")
    sub = parser.add_subparsers(dest="command", required=True)

    def project_command(name: str, help_text: str) -> argparse.ArgumentParser:
        command = sub.add_parser(name, help=help_text)
        command.add_argument("project")
        return command

    init = project_command("init", "初始化项目")
    init.add_argument("--project-id", required=True)
    init.add_argument("--name", required=True)
    project_command("validate", "校验项目")
    project_command("status", "读取当前状态")
    project_command("doctor", "检查 Skill 版本、完整性、旧版残留和运行环境")
    project_command("capabilities", "显示五阶段、七方法和调用关系")
    project_command("handoff", "生成交接")
    project_command("legacy-scan", "检测旧 Skill")
    migrate = project_command("migrate", "迁移旧项目")
    migrate.add_argument("--project-id")
    migrate.add_argument("--name")

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
            result = runtime.validate()
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
            result = runtime.migrate(args.project_id, args.name)
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
