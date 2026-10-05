# ruff: noqa: E501
from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "tools" / "phase39_relational_readout.py"
spec = importlib.util.spec_from_file_location("phase39", MODULE_PATH)
assert spec and spec.loader
phase39 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = phase39
spec.loader.exec_module(phase39)


def test_corpus_is_frozen_size_split_and_group_isolated() -> None:
    corpus = phase39.build_corpus()
    primary = [row for row in corpus["rows"] if row["kind"] == "primary"]
    assert len(primary) == 2400
    assert len(corpus["rows"]) == 2640
    assert Counter(row["split"] for row in primary) == {
        "train": 2000,
        "validation": 200,
        "test": 200,
    }
    groups = {}
    for row in primary:
        groups.setdefault(row["group_id"], set()).add(row["split"])
        assert row["known_predicate"] in phase39.PREDICATES
        assert row["labels"][row["known_predicate"]] in {0, 1}
        assert "Consider the connection from" in row["prompt"]
    assert all(len(splits) == 1 for splits in groups.values())


def test_heldout_domains_and_templates_are_disjoint() -> None:
    corpus = phase39.build_corpus()
    primary = [row for row in corpus["rows"] if row["kind"] == "primary"]
    train = [row for row in primary if row["split"] == "train"]
    test = [row for row in primary if row["split"] == "test"]
    assert {row["domain"] for row in train}.isdisjoint({row["domain"] for row in test})
    assert {row["template_family"] for row in train}.isdisjoint(
        {row["template_family"] for row in test}
    )


def test_diagnostics_cover_required_hard_controls() -> None:
    corpus = phase39.build_corpus()
    counts = Counter(row["kind"] for row in corpus["rows"])
    assert counts["role_reversal"] == 80
    assert counts["entity_renaming"] == 80
    assert counts["same_words_changed_structure"] == 40
    assert counts["easy_explicit_word"] == 40


def test_prepare_produces_hashable_remote_source_and_controller_smoke(tmp_path: Path) -> None:
    result = phase39.prepare(tmp_path)
    assert result["mock"]["status"] == "PASS"
    assert len(result["corpus_hash"]) == 64
    remote = (tmp_path / "source" / "phase39_remote_capture.py").read_text(encoding="utf-8")
    assert "register_forward_hook" in remote
    assert "output_hidden_states" not in remote
    assert (tmp_path / "manifests" / "frozen-manifest.json").exists()


def test_linear_reader_finds_toy_signal_and_uses_masked_labels() -> None:
    rng = phase39.np.random.default_rng(11)
    labels = phase39.np.array([0] * 30 + [1] * 30)
    features = rng.normal(size=(60, 4))
    features[:, 0] += labels * 2.5
    weights, intercept = phase39.fit_logistic(features, labels, penalty=0.003)
    probability = phase39.probabilities(features, weights, intercept)
    assert phase39.metric(labels, probability, 0.5)["balanced_accuracy"] > 0.85


def test_remote_capture_source_compiles_without_model_runtime(tmp_path: Path) -> None:
    path = tmp_path / "capture.py"
    remote = phase39.remote_capture_source()
    path.write_text(remote, encoding="utf-8")
    source = compile(path.read_text(encoding="utf-8"), str(path), "exec")
    assert source is not None
    assert "same_microbatch_repeat" in remote
    assert "cross_layout_diagnostic" in remote
    assert "smoke-features.npz" in remote
