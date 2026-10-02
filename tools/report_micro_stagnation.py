#!/usr/bin/env python3
"""Inference-free qualification analysis; labels join only after observation."""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import math
import statistics
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from mneme.experiments.movement_meters import measure_movement
from mneme.experiments.pressure_meters import measure_pressure_records

Json = dict[str, Any]
CLASSES = ('progress', 'circling', 'unclear')


def distribution(values: Sequence[Any], *, seconds: bool = False) -> Json:
    """Missing, negative and nonfinite measurements remain unavailable."""
    valid = sorted(float(x) for x in values if type(x) in (int, float)
                   and math.isfinite(x) and x >= 0)
    result: Json = {
        'n': len(valid), 'unavailable': len(values) - len(valid),
        'median': statistics.median(valid) if valid else None,
        'p90_nearest_rank': valid[math.ceil(.9 * len(valid)) - 1] if valid else None,
        'maximum': max(valid) if valid else None,
    }
    if seconds:
        result['percent_within_seconds'] = {
            str(limit): 100 * sum(x <= limit for x in valid) / len(valid) if valid else None
            for limit in (1, 3, 5, 10)
        }
    return result


def timing_summary(readings: Sequence[Mapping[str, Any]]) -> Json:
    """Preserve the distinction between HTTP wall, observation wall and server timing."""
    called = [r for r in readings if r.get('model_called') is True]
    return {
        'recorded_attempts': len(readings), 'model_calls': len(called),
        'http_wall_seconds': distribution([r.get('wall_seconds') for r in called], seconds=True),
        'observation_wall_seconds': distribution(
            [r.get('observation_wall_seconds') for r in readings], seconds=True),
        **{key: distribution([r.get(key) for r in called]) for key in (
            'prefill_ms', 'generation_ms', 'input_tokens', 'output_tokens')},
        'native_prompt_tokens': distribution([r.get('native_prompt_tokens') for r in readings]),
    }


def interpreted(row: Mapping[str, Any], variant: Mapping[str, Any]) -> str | None:
    """Revalidate the recorded digit; capped or malformed answers cannot become labels."""
    mapping = variant['output_mapping']
    content, value = row.get('content'), row.get('value')
    if (row.get('available') is not True or row.get('finish_reason') != 'stop'
            or type(value) is not int or not isinstance(content, str)
            or content.strip() != str(value) or str(value) not in mapping):
        return None
    label = mapping[str(value)]
    if label not in CLASSES:
        raise ValueError('unknown output interpretation')
    return str(label)


def passive_checkpoints(records: Sequence[Mapping[str, Any]]) -> list[Json]:
    """Join unchanged passive readings at accepted ages divisible by five."""
    movement = measure_movement(records, windows=(3,))
    pressure = measure_pressure_records(records, windows=(3,))
    grouped: dict[tuple[str, str], dict[str, Json]] = {}
    for row in pressure:
        key = (row['conversation'], row['accepted_turn_id'])
        grouped.setdefault(key, {})[row['source_view']] = row
    output = []
    for row in movement:
        if row['arc_age'] % 5:
            continue
        source_views = grouped[(row['conversation'], row['accepted_turn_id'])]
        common = source_views['participant']
        output.append({
            **{key: row.get(key) for key in (
                'conversation', 'arc_id', 'arc_age', 'turn', 'ordinal', 'accepted_turn_id',
                'gemma_word_count', 'participant_quantities_new_fraction',
                'gemma_phrases_recent_max_jaccard', 'gemma_content_new_fraction')},
            **{key: common.get(key) for key in (
                'context_activation_total', 'context_positive_coverage', 'context_hhi',
                'history_entropy_nats', 'history_effective_count', 'history_context_tv')},
            'pressure_source_views': source_views,
            'movement': row,
        })
    return output


def bank_checkpoints(bank: Mapping[str, Any]) -> dict[str, Json]:
    records = []
    for case in bank['cases']:
        cid = case['case_id']
        for index, exchange in enumerate(case['window']):
            records.append({
                'conversation': cid, 'arc_id': cid, 'turn': index + 1, 'ordinal': index,
                'accepted_turn_id': f'{cid}:{index + 1}',
                'participant_text': exchange['participant_text'],
                'gemma_text': exchange['gemma_text'],
            })
    return {r['conversation']: r for r in passive_checkpoints(records)}


def analyze(bank: Mapping[str, Any], prompts: Mapping[str, Any],
            readings: Sequence[Mapping[str, Any]]) -> Json:
    """Pure, deterministic Phase A gate with fixed denominators and no provider access."""
    cases = {c['case_id']: c for c in bank['cases']}
    variants = {v['prompt_id']: v for v in prompts['variants']}
    if len(cases) != 16 or Counter(c['expected_class'] for c in cases.values()) != {
        'progress': 8, 'circling': 6, 'unclear': 2,
    } or set(variants) != {'binary_a', 'binary_b', 'ternary_a', 'ternary_b'}:
        raise ValueError('the frozen gate requires its 16-case/four-prompt design')
    indexed = {}
    for row in readings:
        key = (row.get('case_id'), row.get('prompt_id'), row.get('repeat'))
        if key[0] not in cases or key[1] not in variants or key[2] not in (1, 2):
            raise ValueError('unknown qualification coordinate')
        if key in indexed:
            raise ValueError('duplicate qualification coordinate')
        indexed[key] = row
    passive = bank_checkpoints(bank)
    matrix = []
    by_variant: Json = {}
    duplicate_checks = []
    for pid, variant in sorted(variants.items()):
        repeat_results = []
        parsed = 0
        for repeat in (1, 2):
            confusion: Json = {c: dict.fromkeys((*CLASSES, 'unavailable'), 0) for c in CLASSES}
            wrong: list[str] = []
            ambiguous: list[Json] = []
            unavailable: list[str] = []
            abstentions: list[str] = []
            for cid, case in sorted(cases.items()):
                row = indexed.get((cid, pid, repeat), {})
                label = interpreted(row, variant)
                expected = case['expected_class']
                confusion[expected][label or 'unavailable'] += 1
                parsed += label is not None
                item = {
                    **{k: v for k, v in passive[cid].items()
                       if k not in {'pressure_source_views', 'movement'}},
                    'normal_response_output_tokens': None,
                    'normal_response_finish_reason': None,
                    'case_id': cid, 'category': case['category'], 'prompt_id': pid,
                    'repeat': repeat, 'expected_class': expected, 'reading': label,
                    'value': row.get('value'), 'content': row.get('content'),
                    'finish_reason': row.get('finish_reason'),
                    'correct_clear': label == expected if expected != 'unclear' else None,
                    'unavailable_reason': (None if label is not None else
                                           row.get('unavailable_reason')
                                           or 'missing or invalid reading'),
                    **{key: row.get(key) for key in (
                        'wall_seconds', 'observation_wall_seconds', 'prefill_ms',
                        'generation_ms', 'input_tokens', 'output_tokens')},
                }
                matrix.append(item)
                if expected == 'unclear':
                    ambiguous.append({'case_id': cid, 'reading': label})
                elif label is not None and label != expected:
                    (abstentions if label == 'unclear' else wrong).append(cid)
                if label is None:
                    unavailable.append(cid)
            progress = confusion['progress']['progress']
            circling = confusion['circling']['circling']
            repeat_results.append({
                'repeat': repeat, 'clear_correct': progress + circling, 'clear_total': 14,
                'recall': {
                    'progress': {'correct': progress, 'total': 8, 'fraction': progress / 8},
                    'circling': {'correct': circling, 'total': 6, 'fraction': circling / 6},
                }, 'confusion': confusion, 'ambiguous_outputs': ambiguous,
                'wrong_clear_cases': wrong, 'uncertain_clear_cases': abstentions,
                'unavailable_cases': unavailable,
                'accuracy_gate': progress + circling >= 11 and progress >= 6 and circling >= 4,
            })
        by_variant[pid] = {
            'repeats': repeat_results, 'parsed': parsed, 'expected_outputs': 32,
            'qualified': parsed >= 30 and all(r['accuracy_gate'] for r in repeat_results),
            'latency': timing_summary([r for r in readings if r.get('prompt_id') == pid]),
        }
        for cid in sorted(cases):
            first, second = (indexed.get((cid, pid, repeat)) for repeat in (1, 2))
            available = (first is not None and second is not None
                         and first.get('model_called') is True
                         and second.get('model_called') is True)
            duplicate_checks.append({
                'case_id': cid, 'prompt_id': pid, 'compared': available,
                'content_and_finish_equal': (all(first.get(k) == second.get(k)
                                                 for k in ('content', 'finish_reason'))
                                            if available and first and second else None),
            })
    pairs = {}
    for form in ('binary', 'ternary'):
        agreements: list[Json] = []
        for repeat in (1, 2):
            clear_agreement = 0
            whole_agreement = 0
            ambiguous_pairs = []
            for cid, case in sorted(cases.items()):
                labels = [interpreted(indexed.get((cid, form + suffix, repeat), {}),
                                      variants[form + suffix]) for suffix in ('_a', '_b')]
                if labels[0] is not None and labels[0] == labels[1]:
                    whole_agreement += 1
                if case['expected_class'] == 'unclear':
                    ambiguous_pairs.append({'case_id': cid, 'readings': labels})
                elif labels[0] is not None and labels[0] == labels[1]:
                    clear_agreement += 1
            agreements.append({'repeat': repeat, 'clear_agreement': clear_agreement,
                               'clear_total': 14, 'whole_agreement': whole_agreement,
                               'whole_total': 16, 'ambiguous_pairs': ambiguous_pairs})
        pairs[form] = {
            'repeats': agreements,
            'qualified': all(by_variant[form + suffix]['qualified'] for suffix in ('_a', '_b'))
            and all(r['clear_agreement'] >= 12 for r in agreements),
        }
    mismatches = [r for r in duplicate_checks if r['content_and_finish_equal'] is False]
    selected = None
    if not mismatches:
        if pairs['ternary']['qualified']:
            selected = 'ternary_a'
        elif pairs['binary']['qualified']:
            selected = 'binary_a'
    return {
        'schema_version': 1, 'phase': 'A', 'recorded_readings': len(readings),
        'expected_readings': 128, 'baseline': {
            'always_progress_clear_correct': 8, 'clear_total': 14,
            'always_progress_clear_accuracy': 8 / 14,
            'ambiguous_binary_accuracy': None,
        }, 'variants': by_variant, 'wording_pairs': pairs,
        'duplicate_replay': {'comparisons': sum(r['compared'] for r in duplicate_checks),
                             'mismatches': mismatches, 'checks': duplicate_checks},
        'selected_prompt': selected, 'phase_a_qualified': selected is not None,
        'latency': timing_summary(readings), 'matrix': matrix, 'passive_checkpoints': passive,
    }


def render_matrix(report: Mapping[str, Any]) -> tuple[str, str]:
    rows = report['matrix']
    columns = ['case_id', 'prompt_id', 'repeat', 'expected_class', 'reading', 'correct_clear',
               'wall_seconds', 'observation_wall_seconds', 'input_tokens', 'output_tokens',
               'unavailable_reason', 'conversation', 'arc_id', 'turn', 'ordinal',
               'accepted_turn_id', 'arc_age', 'context_activation_total',
               'context_positive_coverage', 'context_hhi', 'history_entropy_nats',
               'history_effective_count', 'history_context_tv', 'gemma_word_count',
               'participant_quantities_new_fraction', 'gemma_phrases_recent_max_jaccard',
               'gemma_content_new_fraction', 'normal_response_output_tokens',
               'normal_response_finish_reason']
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator='\n', extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
    md_columns = columns[:6] + ['arc_age', 'gemma_word_count',
                               'participant_quantities_new_fraction',
                               'gemma_phrases_recent_max_jaccard', 'wall_seconds']
    lines = ['| ' + ' | '.join(md_columns) + ' |',
             '| ' + ' | '.join(['---'] * len(md_columns)) + ' |']
    for row in rows:
        lines.append('| ' + ' | '.join(str(row.get(k)) if row.get(k) is not None
                                       else 'unavailable' for k in md_columns) + ' |')
    return stream.getvalue(), '\n'.join(lines) + '\n'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--prompts', type=Path, required=True)
    parser.add_argument('--readings', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    payload = args.readings.read_bytes()
    readings = json.loads(gzip.decompress(payload)
                          if args.readings.suffix == '.gz' else payload)
    report = analyze(json.loads(args.cases.read_text()), json.loads(args.prompts.read_text()),
                     readings)
    args.output.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    (args.output / 'summary.json.gz').write_bytes(gzip.compress(encoded, mtime=0))
    csv_text, md_text = render_matrix(report)
    (args.output / 'matrix.csv').write_text(csv_text)
    (args.output / 'matrix.md').write_text(md_text)


if __name__ == '__main__':
    main()
