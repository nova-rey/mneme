from mneme.hosts import FakeHost
from mneme.state.contracts import StoragePermissions
from mneme.state.storage import SQLiteStore
from tools.compare_pressure_histories import compare_histories


def test_history_diagnostic_is_read_only_and_never_generates(tmp_path, monkeypatch):
    source = tmp_path / "historical.sqlite3"
    with SQLiteStore(source) as store:
        store.create_root(
            permissions=StoragePermissions(True, True, True, True, True, True),
            host_binding=FakeHost().fingerprint().to_dict(),
        )
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}

    def forbidden(*args, **kwargs):
        raise AssertionError("historical diagnostic attempted generation")

    monkeypatch.setattr(FakeHost, "generate", forbidden)
    records = [{
        "conversation": "recorded", "turn": 1,
        "field": {"query": "recorded participant message", "field_seed": 42,
                  "accessibility_distribution": []},
        "historical_strengths": {}, "accessibility_adjustments": {},
    }]
    first = compare_histories(records, source)
    assert first == compare_histories(records, source)
    assert first["provider_calls"] == first["state_writes"] == 0
    assert first["rows"][0]["secondary"]["history_context_tv"] is None
    assert first["rows"][0]["query"] == records[0]["field"]["query"]
    assert first["rows"][0]["field_seed"] == 42
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()} == before
