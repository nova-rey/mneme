from __future__ import annotations

import copy
import json
import socket
import sqlite3

import pytest

from tools.report_micro_stagnation import (
    analyze,
    distribution,
    passive_checkpoints,
    render_matrix,
)


def fixture():
    labels = ['progress'] * 8 + ['circling'] * 6 + ['unclear'] * 2
    bank = {'cases': [
        {'case_id': f'q{i:02}', 'expected_class': label, 'category': label,
         'window': [{'participant_text': f'Measured {turn} ms.',
                     'gemma_text': f'Test the cable after {turn} ms.'} for turn in range(5)]}
        for i, label in enumerate(labels)
    ]}
    prompts = {'variants': [
        {'prompt_id': form + suffix, 'output_mapping': (
            {'0': 'progress', '1': 'circling'} if form == 'binary' else
            {'0': 'progress', '1': 'unclear', '2': 'circling'})}
        for form in ('binary', 'ternary') for suffix in ('_a', '_b')
    ]}
    rows = []
    for case in bank['cases']:
        for variant in prompts['variants']:
            label = case['expected_class']
            mapping = variant['output_mapping']
            value = next((int(k) for k, v in mapping.items() if v == label), 0)
            for repeat in (1, 2):
                rows.append({'case_id': case['case_id'], 'prompt_id': variant['prompt_id'],
                             'repeat': repeat, 'available': True, 'value': value,
                             'content': str(value), 'finish_reason': 'stop',
                             'model_called': True, 'wall_seconds': 2.,
                             'observation_wall_seconds': 3., 'input_tokens': 500,
                             'output_tokens': 2, 'prefill_ms': 1800., 'generation_ms': 100.})
    return bank, prompts, rows


def test_correct_balanced_gate_ternary_preference_and_passive_unavailable():
    report = analyze(*fixture())
    assert report['selected_prompt'] == 'ternary_a'
    assert report['duplicate_replay']['comparisons'] == 64
    assert report['baseline']['always_progress_clear_accuracy'] == 8 / 14
    assert report['baseline']['ambiguous_binary_accuracy'] is None
    row = report['matrix'][0]
    assert row['arc_age'] == 5
    assert row['context_activation_total'] is None
    assert row['history_entropy_nats'] is None
    assert row['gemma_word_count'] > 0
    assert row['normal_response_output_tokens'] is None
    assert report['variants']['ternary_a']['repeats'][0]['ambiguous_outputs'] == [
        {'case_id': 'q14', 'reading': 'unclear'}, {'case_id': 'q15', 'reading': 'unclear'}]


def test_majority_baseline_fails_and_missing_denominators_stay_fixed():
    bank, prompts, rows = fixture()
    for row in rows:
        row.update(value=0, content='0')
    report = analyze(bank, prompts, rows)
    assert report['selected_prompt'] is None
    assert report['variants']['binary_a']['repeats'][0]['clear_correct'] == 8
    partial = analyze(bank, prompts, rows[:1])
    assert partial['selected_prompt'] is None
    assert partial['variants']['binary_a']['expected_outputs'] == 32
    assert partial['variants']['binary_a']['repeats'][1]['clear_total'] == 14


def test_abstention_is_not_correct_clear_and_binary_can_be_selected():
    bank, prompts, rows = fixture()
    for row in rows:
        if row['prompt_id'].startswith('ternary'):
            row.update(value=1, content='1')
    report = analyze(bank, prompts, rows)
    assert report['selected_prompt'] == 'binary_a'
    repeat = report['variants']['ternary_a']['repeats'][0]
    assert repeat['clear_correct'] == 0
    assert len(repeat['uncertain_clear_cases']) == 14
    assert repeat['wrong_clear_cases'] == []


def test_capped_and_malformed_outputs_never_count_as_parsed():
    bank, prompts, rows = fixture()
    for row in rows:
        if row['case_id'] in ('q00', 'q01'):
            row['finish_reason'] = 'length'
        if row['case_id'] == 'q02':
            row['content'] = '0 because progress'
    report = analyze(bank, prompts, rows)
    assert report['selected_prompt'] is None
    assert report['variants']['binary_a']['parsed'] == 26
    assert report['matrix'][0]['reading'] is None


def test_duplicate_content_and_finish_mismatch_blocks_selection():
    bank, prompts, rows = fixture()
    rows[1]['content'] += ' '
    report = analyze(bank, prompts, rows)
    assert report['variants']['binary_a']['qualified']
    assert len(report['duplicate_replay']['mismatches']) == 1
    assert report['selected_prompt'] is None


def test_threshold_and_wording_agreement_boundaries():
    bank, prompts, rows = fixture()
    # Each variant gets 11/14, including 6/8 progress and 5/6 circling,
    # but disjoint errors make the wording pair agree on only 8/14.
    failures = {'_a': {'q00', 'q01', 'q08'}, '_b': {'q02', 'q03', 'q09'}}
    for row in rows:
        if row['case_id'] in failures[row['prompt_id'][-2:]]:
            new = 'circling' if row['case_id'] < 'q08' else 'progress'
            mapping = next(v['output_mapping'] for v in prompts['variants']
                           if v['prompt_id'] == row['prompt_id'])
            row.update(value=next(int(k) for k, v in mapping.items() if v == new))
            row['content'] = str(row['value'])
    report = analyze(bank, prompts, rows)
    assert all(v['qualified'] for v in report['variants'].values())
    assert report['wording_pairs']['ternary']['repeats'][0]['clear_agreement'] == 8
    assert report['selected_prompt'] is None


def test_latency_nearest_rank_and_true_component_missingness():
    stats = distribution([1, 3, 5, 10, 20, None, float('nan'), -1, True], seconds=True)
    assert stats == {'n': 5, 'unavailable': 4, 'median': 5.,
                     'p90_nearest_rank': 20., 'maximum': 20.,
                     'percent_within_seconds': {'1': 20., '3': 40., '5': 60., '10': 80.}}
    bank, prompts, rows = fixture()
    for row in rows:
        row.pop('prefill_ms')
    report = analyze(bank, prompts, rows)
    assert report['latency']['prefill_ms']['n'] == 0
    assert report['latency']['prefill_ms']['median'] is None
    assert report['latency']['http_wall_seconds']['median'] == 2
    assert report['latency']['observation_wall_seconds']['median'] == 3


def test_analysis_pure_replay_inputs_unchanged_no_io(monkeypatch):
    args = fixture()
    before = copy.deepcopy(args)

    def forbidden(*args, **kwargs):
        pytest.fail('analysis attempted external IO')

    monkeypatch.setattr('builtins.open', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(sqlite3, 'connect', forbidden)
    first = analyze(*args)
    assert first == analyze(*args)
    assert args == before
    assert render_matrix(first) == render_matrix(analyze(*args))
    json.dumps(first, allow_nan=False)


def test_duplicate_coordinate_rejected():
    bank, prompts, rows = fixture()
    with pytest.raises(ValueError, match='duplicate qualification'):
        analyze(bank, prompts, rows + [rows[0]])


def test_checkpoint_join_scopes_turn_identity_by_conversation():
    records = []
    for cid, activation in [('first', 2), ('second', 9)]:
        for turn in range(5):
            records.append({
                'conversation': cid, 'arc_id': cid, 'ordinal': turn, 'turn': turn + 1,
                'accepted_turn_id': f't{turn}', 'participant_text': 'Check the sensor.',
                'gemma_text': 'Test the cable.',
                'field': {'active_concepts': [{'contextual_activation': activation}]},
            })
    rows = passive_checkpoints(records)
    assert [(r['conversation'], r['context_activation_total']) for r in rows] == [
        ('first', 2), ('second', 9)]
    assert rows[0]['pressure_source_views']['participant']['conversation'] == 'first'
    assert rows[1]['pressure_source_views']['participant']['conversation'] == 'second'
    csv_text, _ = render_matrix(analyze(*fixture()))
    columns = set(csv_text.splitlines()[0].split(','))
    assert {'arc_id', 'turn', 'ordinal', 'accepted_turn_id'} <= columns
