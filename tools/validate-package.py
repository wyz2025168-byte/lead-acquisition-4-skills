#!/usr/bin/env python3
"""Validate the v4 candidate across structure, semantics, migration and isolation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".py", ".txt", ".csv"}
FORBIDDEN = (
    "/Users/", "/home/", "01_SOURCE_NEW", "03_COURSE_KERNEL", "泰成", "苍南",
    "杨璇", "宋鸿易", "讨厌摘戴", "行政院长", "技术院长", "RCA-G", "70/70 PASS",
)
VERSION = "4.0.0"
REQUIRED_RULES = {
    "E-OUTCOME-MISSING", "E-OUTCOME-SUBSTITUTION", "E-CONTENT-BEFORE-AUDIENCE",
    "E-PERSONA-BEFORE-W3-W6", "E-PERSONA-INSIDE-OUT",
    "E-LOCAL-RANKING-BY-GENERAL-RESEARCH", "E-ONLINE-CONVERTIBILITY-UNKNOWN",
    "E-DATA-REQUEST-NO-DECISION", "E-DATA-REQUEST-OVERSIZED",
    "E-APPROVAL-NO-PROVENANCE", "E-EVIDENCE-SCOPE-MISMATCH",
    "W-LEADING-METRIC-ONLY", "W-W6-UNKNOWN",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files_under(root: Path, include_dist: bool = False) -> set[str]:
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != ".DS_Store" and ".git" not in path.parts
        and "__pycache__" not in path.parts and path.suffix != ".pyc"
        and (include_dist or "dist" not in path.relative_to(root).parts)
    }


def run(command: list[str], cwd: Path) -> tuple[bool, str]:
    process = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    output = (process.stdout + process.stderr).strip()
    return process.returncode == 0, output[-2000:]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", nargs="?", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    root = Path(args.target).expanduser().resolve()
    checks: list[tuple[str, bool, str]] = []
    skills = root / "skills"
    found = sorted(path.name for path in skills.iterdir() if path.is_dir() and (path / "SKILL.md").is_file()) if skills.is_dir() else []
    checks.append(("single_entry_skill", found == ["jw"], str(found)))
    checks.append(("no_symlinks", not any(path.is_symlink() for path in root.rglob("*")), "candidate tree"))
    skill = skills / "jw"
    skill_text = (skill / "SKILL.md").read_text(encoding="utf-8") if (skill / "SKILL.md").is_file() else ""
    frontmatter = re.match(r"^---\n(.*?)\n---\n", skill_text, re.S)
    checks.append(("skill_frontmatter", bool(frontmatter and re.search(r"^name:\s*jw\s*$", frontmatter.group(1), re.M) and re.search(r"^description:\s*\S", frontmatter.group(1), re.M)), "jw/SKILL.md"))

    method_names = (
        "method-positioning.md", "method-audience-stage.md", "method-audience-continuity.md",
        "method-conversion-journey.md", "method-belief-mindshare.md",
        "method-production-presentation.md", "method-orchestration-control.md",
    )
    method_files = [skill / "references" / name for name in method_names]
    stage_files = [skill / "references" / f"stage-{name}.md" for name in ("positioning", "content", "production", "portfolio", "operations")]
    new_references = [skill / "references" / name for name in (
        "business-node-map.md", "outcome-contract.md", "online-convertibility.md",
        "minimum-information-policy.md", "domain-dental-decision-model.md", "failure-catalog.md",
        "business-invariants.json",
    )]
    schemas = [skill / "schemas" / name for name in (
        "outcome-contract.schema.json", "node.schema.json", "alternative.schema.json",
        "information-request.schema.json", "approval-v4.schema.json",
    )]
    required = [skill / "agents" / "openai.yaml", skill / "scripts" / "jw_project.py", skill / "references" / "operating-system.md", skill / "references" / "method-router.md", skill / "references" / "method-registry.json", *method_files, *stage_files, *new_references, *schemas]
    checks.append(("v4_runtime_methods_nodes_and_schemas", all(path.is_file() for path in required), str(len(required))))
    checks.append(("seven_course_methods_preserved", all(re.findall(r"^## ([1-9])\.", path.read_text(encoding="utf-8"), re.M) == list("123456789") for path in method_files), "9 sections x 7"))

    registry_ok = False
    try:
        registry = json.loads((skill / "references" / "method-registry.json").read_text(encoding="utf-8"))
        methods = registry.get("methods", [])
        registry_ok = registry.get("registry_version") == "4.0.0" and len(methods) == 7 and all(all(field in item for field in ("reads_nodes", "writes_nodes", "required_evidence", "stop_conditions")) for item in methods)
    except Exception:
        registry_ok = False
    checks.append(("method_node_contracts", registry_ok, "7 method input/output contracts"))

    invariant_ok = False
    try:
        invariant = json.loads((skill / "references" / "business-invariants.json").read_text(encoding="utf-8"))
        invariant_ok = invariant.get("runtime_version") == VERSION and REQUIRED_RULES.issubset({item.get("code") for item in invariant.get("rules", [])})
    except Exception:
        invariant_ok = False
    checks.append(("business_invariant_registry", invariant_ok, f"{len(REQUIRED_RULES)} required codes"))
    checks.append(("schema_json_parse", all(json.loads(path.read_text(encoding="utf-8")) for path in schemas), "5 schemas"))

    bundle_path = skill / "BUNDLE_MANIFEST.json"
    bundle_ok = bundle_path.is_file()
    if bundle_ok:
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        declared = {item["path"]: item for item in bundle.get("files", [])}
        actual = files_under(skill) - {"BUNDLE_MANIFEST.json"}
        bundle_ok = bundle.get("skill") == "jw" and bundle.get("version") == VERSION and set(declared) == actual and all(sha256(skill / relative) == item["sha256"] and (skill / relative).stat().st_size == item["bytes"] for relative, item in declared.items())
    checks.append(("bundle_integrity", bundle_ok, "jw/BUNDLE_MANIFEST.json"))

    leaked, raw = [], []
    for path in root.rglob("*"):
        if not path.is_file() or "dist" in path.parts or ".git" in path.parts:
            continue
        if path.suffix.lower() in {".docx", ".pdf", ".ndjson", ".jsonl"}:
            raw.append(path.relative_to(root).as_posix())
        if path.suffix.lower() in TEXT_SUFFIXES and path.name != "validate-package.py":
            text = path.read_text(encoding="utf-8")
            if any(marker in text for marker in FORBIDDEN):
                leaked.append(path.relative_to(root).as_posix())
    checks.append(("no_private_or_project_fingerprints", not leaked, str(sorted(set(leaked)))))
    checks.append(("no_raw_private_formats", not raw, str(sorted(set(raw)))))

    unit_ok, unit_output = run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], root)
    checks.append(("business_and_migration_tests", unit_ok, unit_output.splitlines()[-1] if unit_output else "no output"))
    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)
        natural_ok, natural_output = run([sys.executable, "evals/natural/run_eval.py", "--scan", "--manifest", str(temp / "natural.json")], root)
        natural_manifest = json.loads((temp / "natural.json").read_text(encoding="utf-8")) if (temp / "natural.json").is_file() else {}
        checks.append(("natural_eval_prompt_and_fixture_isolation", natural_ok and natural_manifest.get("status") == "PASS", f"scenarios={natural_manifest.get('scenario_count')} failures={len(natural_manifest.get('scan_failures', []))}"))
        model_summary_path = root / "reports" / "v4" / "NATURAL_MODEL_EVAL_SUMMARY.json"
        model_summary = json.loads(model_summary_path.read_text(encoding="utf-8")) if model_summary_path.is_file() else {}
        model_eval_ok = (
            model_summary.get("natural_eval_passed") is True
            and model_summary.get("run_count") == 21
            and model_summary.get("successful_runs") == 21
            and model_summary.get("hard_failure_total") == 0
            and model_summary.get("passing_scenarios", 0) >= model_summary.get("passing_scenarios_required", 5)
            and model_summary.get("rubric_sha256") == natural_manifest.get("rubric_sha256")
        )
        checks.append(("independent_model_blind_eval", model_eval_ok, f"runs={model_summary.get('successful_runs')}/21 scenarios={model_summary.get('passing_scenarios')}/7 hard_failures={model_summary.get('hard_failure_total')}"))
        replay_ok, _ = run([sys.executable, "tools/run-synthetic-replay.py", "--output", str(temp / "replay.json")], root)
        replay = json.loads((temp / "replay.json").read_text(encoding="utf-8")) if (temp / "replay.json").is_file() else {}
        checks.append(("deidentified_high_ticket_replay", replay_ok and replay.get("passed") == 10 and replay.get("failed") == 0, f"{replay.get('passed')}/10"))
        install_root = temp / "clean-install"
        installed_skill = install_root / ".agents" / "skills" / "jw"
        installed_skill.parent.mkdir(parents=True)
        shutil.copytree(skill, installed_skill)
        doctor_ok, doctor_output = run([sys.executable, str(installed_skill / "scripts" / "jw_project.py"), "doctor", str(install_root)], install_root)
        checks.append(("clean_install_doctor", doctor_ok, doctor_output.splitlines()[-1] if doctor_output else "no output"))

    package_path = root / "PACKAGE_MANIFEST.json"
    package_ok = package_path.is_file()
    if package_ok:
        package = json.loads(package_path.read_text(encoding="utf-8"))
        declared = {item["path"]: item for item in package.get("files", [])}
        actual = files_under(root) - {"PACKAGE_MANIFEST.json", "SHA256SUMS.txt"}
        package_ok = package.get("schema_version") == "4.0" and package.get("version") == f"v{VERSION}" and package.get("file_count") == len(declared) and set(declared) == actual and all(sha256(root / relative) == item["sha256"] and (root / relative).stat().st_size == item["bytes"] for relative, item in declared.items())
    checks.append(("package_manifest_integrity", package_ok, "PACKAGE_MANIFEST.json"))
    sums = root / "SHA256SUMS.txt"
    sums_ok = sums.is_file()
    if sums_ok:
        declared_sums = {}
        for line in sums.read_text(encoding="utf-8").splitlines():
            digest, separator, relative = line.partition("  ")
            if not separator:
                sums_ok = False
                break
            declared_sums[relative] = digest
        expected = files_under(root) - {"SHA256SUMS.txt"}
        sums_ok = sums_ok and set(declared_sums) == expected and all(sha256(root / relative) == digest for relative, digest in declared_sums.items())
    checks.append(("root_checksums", sums_ok, "SHA256SUMS.txt"))

    release = json.loads((root / "RELEASE_MANIFEST.json").read_text(encoding="utf-8")) if (root / "RELEASE_MANIFEST.json").is_file() else {}
    archive = root / "dist" / f"lead-acquisition-4-skills-v{VERSION}.zip"
    archive_ok = archive.is_file() and (root / "dist" / "SHA256SUMS.txt").is_file()
    if archive_ok:
        expected_line = f"{sha256(archive)}  {archive.name}"
        archive_ok = (root / "dist" / "SHA256SUMS.txt").read_text(encoding="utf-8").strip() == expected_line
        with zipfile.ZipFile(archive) as handle:
            expected_names = {f"lead-acquisition-4-skills/{relative}" for relative in files_under(root)}
            archive_ok = archive_ok and set(handle.namelist()) == expected_names and handle.testzip() is None
    checks.append(("archive_integrity", archive_ok, archive.name))
    disclosure_ok = release.get("version") == f"v{VERSION}" and release.get("publication_status") == "FIELD_VALIDATION_RELEASE_PUBLISHED" and release.get("external_actions_require") == "PUBLISH" and bool(release.get("unverified_capabilities"))
    checks.append(("honest_release_disclosure", disclosure_ok, str(release.get("publication_status"))))
    checks.append(("structural_only_not_release_gate", all("--structural-only" not in command for command in release.get("test_commands", [])), "release test commands"))

    failed = [name for name, ok, _ in checks if not ok]
    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'} {name}: {detail}")
    print(json.dumps({"status": "PASS" if not failed else "FAIL", "checks": len(checks), "failed": failed}, ensure_ascii=False))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
