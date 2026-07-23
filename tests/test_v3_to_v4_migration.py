from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tests._helpers import ProjectRuntime


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


class MigrationTests(unittest.TestCase):
    def _make_v3(self, root: Path, leading_success: bool = False) -> str:
        project = root / ".jw-project"
        project.mkdir()
        state = {
            "schema_version": "jw.project-state.v3",
            "runtime_version": "3.0.0",
            "project_id": "PRJ-V3",
            "project_name": "Synthetic v3",
            "active_stage": "POSITIONING",
        }
        (project / "project-state.json").write_text(json.dumps(state), encoding="utf-8")
        for name in ("claims", "decisions", "approvals", "experiments", "feedback"):
            (project / f"{name}.ndjson").write_text("", encoding="utf-8")
        if leading_success:
            claim = {"claim_id": "CLM-OLD", "statement": "到店是成功", "truth_status": "CONFIRMED_FACT", "source_refs": ["SRC-OLD"]}
            (project / "claims.ndjson").write_text(json.dumps(claim, ensure_ascii=False) + "\n", encoding="utf-8")
        (project / "source-registry.json").write_text(json.dumps({"sources": [{"source_id": "SRC-OLD", "title": "legacy", "source_type": "legacy", "scope": {}}]}), encoding="utf-8")
        for name, key in (("entities", "entities"), ("artifact-registry", "artifacts"), ("content-inventory", "content")):
            (project / f"{name}.json").write_text(json.dumps({key: []}), encoding="utf-8")
        return tree_hash(project)

    def test_r15_migration_is_idempotent_and_keeps_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = self._make_v3(root, True)
            runtime = ProjectRuntime(root)
            first = runtime.migrate(None, None, to_version=4)
            backup = Path(first["backup"])
            self.assertEqual(before, tree_hash(backup))
            state_hash = runtime.state()["state_hash"]
            second = runtime.migrate(None, None, to_version=4)
            self.assertFalse(second["migrated"])
            self.assertEqual(state_hash, runtime.state()["state_hash"])
            self.assertTrue((runtime.root / "migration-report.json").is_file())

    def test_rollback_restores_v3_and_quarantines_v4(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = self._make_v3(root, True)
            runtime = ProjectRuntime(root)
            runtime.migrate(None, None, to_version=4)
            result = runtime.rollback_migration()
            self.assertTrue(result["rolled_back"])
            self.assertFalse(result["data_deleted"])
            self.assertEqual(before, tree_hash(root / ".jw-project"))
            self.assertEqual("jw.project-state.v3", json.loads((root / ".jw-project" / "project-state.json").read_text(encoding="utf-8"))["schema_version"])
            self.assertTrue(Path(result["v4_quarantine"]).is_dir())


if __name__ == "__main__":
    unittest.main()
