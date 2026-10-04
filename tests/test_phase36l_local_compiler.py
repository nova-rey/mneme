"""Model-free contract checks for the bounded Phase 3.6L research runner."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _module():
    path = Path(__file__).parents[1] / "tools" / "phase36l_local_compiler.py"
    spec = importlib.util.spec_from_file_location("phase36l_local_compiler", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_frozen_corpus_has_diverse_training_and_heldout_targets() -> None:
    runner = _module()
    assert len(runner.TRAINING) == 48
    assert len(runner.HELD_OUT) == 8
    assert len({target.identifier for target in runner.TRAINING + runner.HELD_OUT}) == 56
    assert all(target.role == "training" for target in runner.TRAINING)
    assert all(target.role == "held_out" for target in runner.HELD_OUT)
    assert len({target.category for target in runner.TRAINING}) >= 12
    assert sum(target.category == "relational_structural" for target in runner.HELD_OUT) >= 2


def test_balanced_contrast_keeps_target_present_on_both_sides() -> None:
    runner = _module()
    target = runner.HELD_OUT[0]
    positive, negative = runner.contrast_pair(target, 0)
    assert target.description in positive and target.description in negative
    assert "useful organizing lens" in positive
    assert "unavailable for organizing" in negative
    assert runner.CONTRAST_CONTEXTS[0] in positive
    assert runner.CONTRAST_CONTEXTS[0] in negative


def test_control_vector_layer_contract_is_explicit() -> None:
    runner = _module()
    payload = runner.corpus(Path("/irrelevant"))
    contract = payload["control_vector_layer_identity"]
    assert contract["capture"] == "ignore l_out layer zero"
    assert contract["directions"] == list(range(1, 42))
    assert contract["hidden_size"] == 2560
