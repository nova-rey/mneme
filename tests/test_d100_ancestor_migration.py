"""Copy-only developed-ancestor migration contracts."""

import json

from mneme.state.contracts import StoragePermissions
from mneme.state.storage import SQLiteStore
from tools.migrate_d100_ancestor import migrate


def test_d100_migration_is_copy_only_and_restartable(tmp_path):
    source = tmp_path / "historical.sqlite3"
    destination = tmp_path / "d100.compact.sqlite3"
    manifest_path = tmp_path / "d100.manifest.json"
    with SQLiteStore(source) as store:
        store.create_root(permissions=StoragePermissions(store=True, export=True))

    manifest = migrate(source, destination, manifest_path, ancestor_name="fixture-D100")

    assert manifest["normative_status"] == "reusable_developed_ancestor_not_normative_reference"
    assert manifest["equivalence"]["core_state"] is True
    assert manifest["equivalence"]["semantic_bindings"] is True
    assert manifest["migration"]["historical_source_mutated"] is False
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["compact"]["state_digest"]
    assert destination.exists()
    assert source.exists()
