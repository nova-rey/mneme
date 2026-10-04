from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _module():
    path = Path(__file__).parents[1] / "tools" / "phase37_semantic_vector_hammer.py"
    spec = importlib.util.spec_from_file_location("phase37", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_frozen_targets_are_cross_domain_and_have_balanced_contrasts() -> None:
    runner = _module()
    assert len(runner.TARGETS) == 3
    for target in runner.TARGETS:
        assert len(target.contrasts) == 16
        assert len(target.evaluation_prompts) == 2
        assert all(positive != negative for positive, negative in target.contrasts)


def test_control_contract_preserves_explicit_gemma_directions() -> None:
    runner = _module()
    item = runner.manifest(Path("/tmp/phase37-test"))
    assert item["layer_mapping"]["ignored_capture"] == "l_out layer zero"
    assert item["layer_mapping"]["directions"] == list(range(1, 42))


def test_evaluation_prompts_do_not_name_target_domains() -> None:
    runner = _module()
    forbidden = {
        "ecological_succession": ("ecolog", "succession", "pioneer", "ecosystem"),
        "musical_counterpoint": ("music", "counterpoint", "melody", "harmony", "rhythm"),
        "defense_in_depth": ("immune", "antibod", "pathogen", "infection", "biolog"),
    }
    for target in runner.TARGETS:
        text = " ".join(target.evaluation_prompts).lower()
        assert not any(token in text for token in forbidden[target.identifier])
