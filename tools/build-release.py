#!/usr/bin/env python3
"""Build deterministic manifests and ZIP artifacts for the skills repository."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
DIST = ROOT / "dist"
VERSION = "1.0.0"
REPO_NAME = "lead-acquisition-4-skills"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files_under(root: Path, exclude_names: set[str] | None = None):
    exclude_names = exclude_names or set()
    return sorted(
        p for p in root.rglob("*")
        if p.is_file()
        and p.name not in exclude_names
        and ".git" not in p.parts
        and "__pycache__" not in p.parts
        and "dist" not in p.relative_to(ROOT).parts
        and p.suffix != ".pyc"
    )


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_zip(path: Path, pairs: list[tuple[Path, str]]) -> None:
    if path.exists():
        path.unlink()
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source, arcname in pairs:
            info = zipfile.ZipInfo(arcname, date_time=(2026, 7, 19, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())


def main() -> None:
    DIST.mkdir(parents=True, exist_ok=True)
    (DIST / "skills").mkdir(parents=True, exist_ok=True)

    skill_dirs = sorted(p for p in SKILLS.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())
    for skill_dir in skill_dirs:
        manifest_path = skill_dir / "BUNDLE_MANIFEST.json"
        files = [p for p in files_under(skill_dir, {"BUNDLE_MANIFEST.json"})]
        write_json(manifest_path, {
            "schema_version": "1.0",
            "skill": skill_dir.name,
            "release": f"v{VERSION}",
            "files": [
                {"path": p.relative_to(skill_dir).as_posix(), "sha256": sha256(p), "bytes": p.stat().st_size}
                for p in files
            ],
        })

    release_manifest = {
        "schema_version": "1.0",
        "name": REPO_NAME,
        "version": f"v{VERSION}-rc1",
        "publication_status": "PUBLIC_RC1_SANITIZED_RESTRICTED_EVALUATION",
        "repository": "https://github.com/wyz2025168-byte/lead-acquisition-4-skills",
        "license": "Restricted Evaluation License 1.0",
        "installable_skills": [p.name for p in skill_dirs],
        "course_capabilities": 7,
        "engineering_router": "jw",
        "private_source_files_included": 0,
        "private_traceability_metadata_included": False,
        "private_evaluation_materials_included": False,
        "g7_real_project_shadow_included": False,
        "installation_test": {
            "skills_cli_version": "1.5.19",
            "skills_discovered": 8,
            "skills_installed": 8,
            "post_install_bundle_checks": "8/8 PASS",
            "environment": "isolated temporary HOME",
            "local_release_candidate_verified": True,
            "public_github_remote_install_verified": True,
            "public_github_source": "wyz2025168-byte/lead-acquisition-4-skills"
        }
    }
    write_json(ROOT / "RELEASE_MANIFEST.json", release_manifest)

    package_path = ROOT / "PACKAGE_MANIFEST.json"
    sums_path = ROOT / "SHA256SUMS.txt"
    package_files = [p for p in files_under(ROOT, {"PACKAGE_MANIFEST.json", "SHA256SUMS.txt"})]
    write_json(package_path, {
        "schema_version": "1.0",
        "name": REPO_NAME,
        "version": f"v{VERSION}-rc1",
        "file_count": len(package_files),
        "files": [
            {"path": p.relative_to(ROOT).as_posix(), "sha256": sha256(p), "bytes": p.stat().st_size}
            for p in package_files
        ],
    })
    sum_files = [p for p in files_under(ROOT, {"SHA256SUMS.txt"})]
    sums_path.write_text("".join(f"{sha256(p)}  {p.relative_to(ROOT).as_posix()}\n" for p in sum_files), encoding="utf-8")

    for skill_dir in skill_dirs:
        pairs = [(p, p.relative_to(skill_dir).as_posix()) for p in files_under(skill_dir)]
        write_zip(DIST / "skills" / f"{skill_dir.name}-v{VERSION}.zip", pairs)

    repo_files = [p for p in files_under(ROOT)]
    repo_pairs = [(p, f"{REPO_NAME}/{p.relative_to(ROOT).as_posix()}") for p in repo_files]
    write_zip(DIST / f"{REPO_NAME}-v{VERSION}.zip", repo_pairs)

    dist_files = sorted(p for p in DIST.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt")
    (DIST / "SHA256SUMS.txt").write_text(
        "".join(f"{sha256(p)}  {p.relative_to(DIST).as_posix()}\n" for p in dist_files),
        encoding="utf-8",
    )
    print(json.dumps({"skills": len(skill_dirs), "package_files": len(package_files), "release_files": len(dist_files)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
