#!/usr/bin/env python3
"""Pure paired comparison, only after reasoning replay/control validation passes."""
from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any

from tools.report_micro_stagnation import interpreted, timing_summary

Json = dict[str, Any]


def compare(bank: Json, prompts: Json, off: list[Json], on: list[Json]) -> Json:
    """Reuse expected classes; repeat one counts accuracy, both repeats verify replay."""
    variants = {p['prompt_id']: p for p in prompts['variants']}
    cases = {c['case_id']: c for c in bank['cases']}
    expected = {(c, p, r) for c in cases for p in variants for r in (1, 2)}
    maps = []
    for condition, rows in [('off', off), ('on', on)]:
        keyed = {(r['case_id'], r['prompt_id'], r['repeat']): r for r in rows}
        if len(rows) != len(expected) or set(keyed) != expected:
            raise ValueError('incomplete or duplicate coordinates; do not interpret differences')
        for c in cases:
            for p in variants:
                a, b = (keyed[c, p, r] for r in (1, 2))
                keys: tuple[str, ...] = ('content', 'finish_reason', 'request_sha256')
                if condition == 'on':
                    keys += ('reasoning_content',)
                    if not a.get('reasoning_content') or a.get('finish_reason') != 'stop':
                        raise ValueError('reasoning ON not established or capped')
                if any(a.get(k) != b.get(k) for k in keys):
                    raise ValueError('duplicate replay failed; do not interpret differences')
        maps.append(keyed)
    results: Json = {'prompts': {}, 'case_matrix': [], 'wording': {}}
    for p, variant in variants.items():
        stats: Json = {}
        for condition, keyed in zip(('off', 'on'), maps, strict=True):
            labels = {c: interpreted(keyed[c, p, 1], variant) for c in cases}
            stats[condition] = {
                'clear_correct': sum(labels[c] == cases[c]['expected_class'] for c in cases
                                     if cases[c]['expected_class'] != 'unclear'),
                'clear_total': sum(c['expected_class'] != 'unclear' for c in cases.values()),
                'progress_correct': sum(labels[c] == 'progress' for c in cases
                                        if cases[c]['expected_class'] == 'progress'),
                'circling_correct': sum(labels[c] == 'circling' for c in cases
                                        if cases[c]['expected_class'] == 'circling'),
                'fixation_correct': sum(labels[c] == 'circling' for c in ('q11', 'q12')),
                'productive_false_circling': [c for c in cases
                                              if cases[c]['expected_class'] == 'progress'
                                              and labels[c] == 'circling'],
                'ambiguous': {c: labels[c] for c in cases
                              if cases[c]['expected_class'] == 'unclear'},
                'valid_outputs': sum(interpreted(keyed[c, p, r], variant) is not None
                                     for c in cases for r in (1, 2)),
                'output_classes_repeat_one': dict(Counter(labels.values())),
            }
        results['prompts'][p] = stats
        for c, case in cases.items():
            a, b = (keyed[c, p, 1] for keyed in maps)
            results['case_matrix'].append({
                'case_id': c, 'prompt_id': p, 'expected': case['expected_class'],
                'off': interpreted(a, variant), 'on': interpreted(b, variant),
                'on_final': b.get('content'), 'on_finish': b.get('finish_reason'),
                'on_output_tokens': b.get('output_tokens'),
                'on_reasoning_tokens': b.get('reasoning_tokens'),
                'on_wall_seconds': b.get('wall_seconds'),
            })
    for fmt in ('binary', 'ternary'):
        results['wording'][fmt] = {}
        for condition, keyed in zip(('off', 'on'), maps, strict=True):
            agree = []
            for c in cases:
                label_a, label_b = (interpreted(keyed[c, fmt + '_' + v, 1], variants[fmt + '_' + v])
                        for v in ('a', 'b'))
                if label_a is not None and label_a == label_b:
                    agree.append(c)
            results['wording'][fmt][condition] = {
                'agree_all': len(agree), 'total_all': len(cases),
                'agree_clear': sum(cases[c]['expected_class'] != 'unclear' for c in agree),
                'disagreement_cases': [c for c in cases if c not in agree],
            }
    results['timings'] = {'off': timing_summary(off), 'on': timing_summary(on)}
    return results


def load(path: Path) -> Any:
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bank', 'prompts', 'off', 'on', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    report = compare(load(args.bank), load(args.prompts), load(args.off), load(args.on))
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
