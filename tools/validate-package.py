#!/usr/bin/env python3
"""Validate the portable Agent Skills repository."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
EXPECTED = {
    "jw",
    "jw-positioning",
    "jw-lock",
    "jw-circle",
    "jw-convert",
    "jw-grow",
    "jw-production",
    "jw-orchestrator",
}
COURSE_SKILLS = EXPECTED - {"jw"}
PRIVATE_MARKERS = ("/Users/", "/home/", "\\Users\\")
PUBLIC_METADATA_FORBIDDEN = (
    "01_SOURCE_NEW/",
    "03_COURSE_MAP/",
    "04_SKILLS/_contracts/",
    "05_EVAL/",
    "06_PROJECTS/",
    "07_OUTPUTS/",
    "controlled_path",
    "source_sha256",
    "rubric_ids",
    "gold_case_file",
    "RCA-G",
    "AMB-G",
    "D-G0",
    "D-G1",
    "D-G2",
    "D-G3",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    checks: list[tuple[str, bool]] = []
    found = {p.name for p in SKILLS.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()}
    checks.append(("skill_set_8", found == EXPECTED))
    checks.append(("course_skill_set_7", len(found & COURSE_SKILLS) == 7))

    frontmatter_ok = True
    bundle_ok = True
    private_path_ok = True
    portable_mode_ok = True
    public_metadata_ok = True
    for name in sorted(found):
        skill_dir = SKILLS / name
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        frontmatter_ok &= bool(match and re.search(rf"^name:\s*{re.escape(name)}\s*$", match.group(1), re.M) and "description:" in match.group(1))
        private_path_ok &= not any(marker in text for marker in PRIVATE_MARKERS)
        portable_mode_ok &= name == "jw" or "standalone_manual" in text
        manifest = skill_dir / "BUNDLE_MANIFEST.json"
        validator = skill_dir / "scripts" / "validate-bundle.py"
        bundle_ok &= manifest.is_file() and validator.is_file()
        if manifest.is_file():
            data = json.loads(manifest.read_text(encoding="utf-8"))
            for item in data.get("files", []):
                path = skill_dir / item["path"]
                bundle_ok &= path.is_file() and sha256(path) == item["sha256"]
        if name != "jw":
            public_paths = [
                skill_dir / "SKILL.md",
                skill_dir / "references" / "course-rules.md",
                skill_dir / "references" / "source-map.json",
                skill_dir / "schemas" / "contract-binding.json",
                skill_dir / "tests" / "gold-binding.json",
                skill_dir / "tests" / "evaluation-binding.json",
            ]
            for path in public_paths:
                public_text = path.read_text(encoding="utf-8")
                public_metadata_ok &= not any(marker in public_text for marker in PUBLIC_METADATA_FORBIDDEN)
                public_metadata_ok &= not bool(re.search(r"\bS\d{2}:L", public_text))

    checks.extend([
        ("frontmatter", frontmatter_ok),
        ("bundle_manifests", bundle_ok),
        ("no_private_absolute_paths_in_skill_instructions", private_path_ok),
        ("standalone_manual_boundary", portable_mode_ok),
        ("public_metadata_sanitized", public_metadata_ok),
        ("raw_course_files_excluded", not any(p.suffix.lower() in {".docx", ".pdf"} for p in ROOT.rglob("*"))),
        ("internal_control_dirs_excluded", not any((ROOT / name).exists() for name in ("00_CONTROL", "01_SOURCE_NEW", "05_EVAL", "06_PROJECTS", "07_OUTPUTS"))),
        ("license_status_explicit", (ROOT / "LICENSE.md").is_file()),
        ("source_of_truth_explicit", (ROOT / "SOURCE_OF_TRUTH.md").is_file()),
        ("install_command_present", "npx -y skills add" in (ROOT / "README.md").read_text(encoding="utf-8")),
    ])

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'} {name}")
    print(json.dumps({"passed": len(checks) - len(failed), "failed": len(failed), "total": len(checks)}, ensure_ascii=False))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
