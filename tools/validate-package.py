#!/usr/bin/env python3
"""Validate a single-entry JW v2 candidate or public release."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path


TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".py", ".txt"}
FORBIDDEN = (
    "/Users/",
    "/home/",
    "01_SOURCE_NEW",
    "03_COURSE_KERNEL",
    "泰成",
    "苍南",
    "杨璇",
    "宋鸿易",
    "讨厌摘戴",
    "行政院长",
    "技术院长",
    "RCA-G",
    "70/70 PASS",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files_under(root: Path, include_dist: bool = False) -> set[str]:
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path.name != ".DS_Store"
        and ".git" not in path.parts
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
        and (include_dist or "dist" not in path.relative_to(root).parts)
    }


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
    required = [skill / "agents" / "openai.yaml", skill / "scripts" / "jw_project.py", skill / "references" / "operating-system.md", skill / "references" / "stage-positioning.md", skill / "references" / "stage-content.md", skill / "references" / "stage-production.md", skill / "references" / "stage-portfolio.md", skill / "references" / "stage-operations.md"]
    checks.append(("runtime_and_five_stages", all(path.is_file() for path in required), str(len(required))))
    checks.append(("no_public_course_stage_codes", not any(re.search(r"\bC(?:00|10|20|30|40|50|90)\b", path.read_text(encoding="utf-8")) for path in skill.rglob("*") if path.is_file() and path.suffix in TEXT_SUFFIXES), "skills/jw"))
    bundle_path = skill / "BUNDLE_MANIFEST.json"
    bundle_ok = bundle_path.is_file()
    if bundle_ok:
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        declared = {item["path"]: item for item in bundle.get("files", [])}
        actual = files_under(skill) - {"BUNDLE_MANIFEST.json"}
        bundle_ok = bundle.get("skill") == "jw" and set(declared) == actual and all(sha256(skill / relative) == item["sha256"] and (skill / relative).stat().st_size == item["bytes"] for relative, item in declared.items())
    checks.append(("bundle_integrity", bundle_ok, "jw/BUNDLE_MANIFEST.json"))
    leaked = []
    raw = []
    for path in root.rglob("*"):
        if not path.is_file() or "dist" in path.parts:
            continue
        if path.suffix.lower() in {".docx", ".pdf", ".ndjson", ".jsonl"}:
            raw.append(path.relative_to(root).as_posix())
        if path.suffix.lower() in TEXT_SUFFIXES and path.name != "validate-package.py":
            text = path.read_text(encoding="utf-8")
            if any(marker in text for marker in FORBIDDEN):
                leaked.append(path.relative_to(root).as_posix())
    checks.append(("no_private_or_project_fingerprints", not leaked, str(sorted(set(leaked)))))
    checks.append(("no_raw_private_formats", not raw, str(sorted(set(raw)))))
    package_path = root / "PACKAGE_MANIFEST.json"
    package_ok = package_path.is_file()
    if package_ok:
        package = json.loads(package_path.read_text(encoding="utf-8"))
        declared = {item["path"]: item for item in package.get("files", [])}
        actual = files_under(root) - {"PACKAGE_MANIFEST.json", "SHA256SUMS.txt"}
        package_ok = package.get("file_count") == len(declared) and set(declared) == actual and all(sha256(root / relative) == item["sha256"] and (root / relative).stat().st_size == item["bytes"] for relative, item in declared.items())
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
    version = str(release.get("version", "")).removeprefix("v")
    archive = root / "dist" / f"lead-acquisition-4-skills-v{version}.zip"
    archive_ok = archive.is_file() and (root / "dist" / "SHA256SUMS.txt").is_file()
    if archive_ok:
        expected_line = f"{sha256(archive)}  {archive.name}"
        archive_ok = (root / "dist" / "SHA256SUMS.txt").read_text(encoding="utf-8").strip() == expected_line
        with zipfile.ZipFile(archive) as handle:
            expected_names = {f"lead-acquisition-4-skills/{relative}" for relative in files_under(root)}
            archive_ok = archive_ok and set(handle.namelist()) == expected_names and handle.testzip() is None
    checks.append(("archive_integrity", archive_ok, archive.name))
    checks.append(("field_validation_disclosure", bool(release.get("field_validation_notice_required")) and release.get("validation", {}).get("G7") == "DEFERRED_TO_FIELD_VALIDATION" and release.get("validation", {}).get("G8") == "DEFERRED_TO_FIELD_VALIDATION", str(release.get("publication_status"))))
    failed = [name for name, ok, _ in checks if not ok]
    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'} {name}: {detail}")
    print(json.dumps({"status": "PASS" if not failed else "FAIL", "checks": len(checks), "failed": failed}, ensure_ascii=False))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
