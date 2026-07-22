#!/usr/bin/env python3
"""Rebuild public v3.0.0 manifests and deterministic archive."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "jw"
DIST = ROOT / "dist"
VERSION = "3.0.0"
NAME = "lead-acquisition-4-skills"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files_under(root: Path, exclude: set[str] | None = None) -> list[Path]:
    exclude = exclude or set()
    return sorted(
        path for path in root.rglob("*")
        if path.is_file()
        and path.name not in exclude
        and path.name != ".DS_Store"
        and ".git" not in path.parts
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
        and "dist" not in path.relative_to(ROOT).parts
    )


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_zip(path: Path, members: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source in members:
            relative = source.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(f"{NAME}/{relative}", date_time=(2026, 7, 22, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())


def main() -> None:
    if not (SKILL / "SKILL.md").is_file():
        raise SystemExit("Missing skills/jw/SKILL.md")
    skill_files = files_under(SKILL, {"BUNDLE_MANIFEST.json"})
    write_json(
        SKILL / "BUNDLE_MANIFEST.json",
        {
            "schema_version": "3.0",
            "skill": "jw",
            "version": VERSION,
            "release": f"v{VERSION}",
            "files": [
                {"path": path.relative_to(SKILL).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size}
                for path in skill_files
            ],
        },
    )
    package_files = files_under(ROOT, {"PACKAGE_MANIFEST.json", "SHA256SUMS.txt"})
    write_json(
        ROOT / "PACKAGE_MANIFEST.json",
        {
            "schema_version": "3.0",
            "name": NAME,
            "version": f"v{VERSION}",
            "file_count": len(package_files),
            "files": [
                {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path), "bytes": path.stat().st_size}
                for path in package_files
            ],
        },
    )
    sum_files = files_under(ROOT, {"SHA256SUMS.txt"})
    (ROOT / "SHA256SUMS.txt").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(ROOT).as_posix()}\n" for path in sum_files),
        encoding="utf-8",
    )
    archive = DIST / f"{NAME}-v{VERSION}.zip"
    write_zip(archive, files_under(ROOT))
    (DIST / "SHA256SUMS.txt").write_text(f"{sha256(archive)}  {archive.name}\n", encoding="utf-8")
    print(json.dumps({"skills": ["jw"], "package_files": len(package_files), "archive": str(archive), "sha256": sha256(archive)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
