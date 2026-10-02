"""Comparison cannot turn replay failure or missing coordinates into semantic evidence."""
import copy
from pathlib import Path

import pytest

from tools.report_micro_reasoning import compare, load

BASE = Path(__file__).parents[1] / 'docs/experiments/micro_stagnation'


def inputs():
    bank = load(BASE / 'qualification_cases.json')
    prompts = load(BASE / 'prompts.json')
    off = load(BASE / 'phase_a/readings.json.gz')
    on = copy.deepcopy(off)
    for row in on:
        row['reasoning_content'] = 'synthetic test reasoning'
    return bank, prompts, off, on


def test_matched_comparison_and_unchanged_inputs():
    data = inputs()
    before = copy.deepcopy(data)
    result = compare(*data)
    assert data == before
    assert compare(*data) == result
    assert result['prompts']['binary_a']['off']['clear_correct'] == 10
    assert result['prompts']['binary_a']['on']['circling_correct'] == 2
    assert result['prompts']['ternary_a']['on']['ambiguous']['q15'] == 'unclear'
    assert all(row['on_reasoning_tokens'] is None for row in result['case_matrix'])


def test_same_final_different_reasoning_is_uninterpretable():
    data = inputs()
    data[3][1]['reasoning_content'] = 'different'
    with pytest.raises(ValueError, match='duplicate replay'):
        compare(*data)


def test_missing_coordinate_is_uninterpretable():
    data = inputs()
    data[3].pop()
    with pytest.raises(ValueError, match='incomplete'):
        compare(*data)


def test_final_digit_only_no_reasoning_rescue():
    data = inputs()
    for row in data[3][:2]:
        row['content'] = 'The answer is 0'
        row['reasoning_content'] = '0'
    result = compare(*data)
    assert result['prompts']['binary_a']['on']['valid_outputs'] == 30
    assert result['prompts']['binary_a']['on']['clear_correct'] == 9
