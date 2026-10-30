#!/usr/bin/env python3
"""Calculate SR, SPL, IE metrics by comparing two JSON files produced by eval_checkpoint.py.

Usage:
    python eval_metrics.py --ref <ref.json> --eval <eval.json> --output <output_file>
"""

import argparse
import json
import math
import os
import re

GROUP_PATTERN = re.compile(r'(Short|Medium|Long)')


def clean_nan(value):
    """Convert NaN/Inf to None for JSON serialization."""
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
    return value


def compare_steps(ref_data, eval_data, output_file):
    """Compare two episode maps and calculate SR, SPL, IE metrics."""

    common = sorted(set(ref_data.keys()) & set(eval_data.keys()))
    only_ref = sorted(set(ref_data.keys()) - set(eval_data.keys()))
    only_eval = sorted(set(eval_data.keys()) - set(ref_data.keys()))

    # Per-task metrics (ref is human, always successful)
    task_results = []
    for filename in common:
        ref_steps = clean_nan(ref_data[filename].get('episode_length'))
        eval_steps = clean_nan(eval_data[filename].get('episode_length'))
        eval_ok = eval_data[filename].get('is_successful') == 1.0

        match = GROUP_PATTERN.search(filename)
        group = match.group(1) if match else 'Other'

        if ref_steps is not None and eval_steps is not None and ref_steps > 0 and eval_steps > 0:
            raw_ratio = min(ref_steps / eval_steps, 1.0)
            eff = raw_ratio if eval_ok else 0.0
            waste = (eval_steps / ref_steps) if not eval_ok else 0.0
        else:
            eff = 0.0
            waste = 0.0

        task_results.append({
            'task_name': filename,
            'goal': eval_data[filename].get('goal'),
            'ref': clean_nan(ref_steps),
            'eval': clean_nan(eval_steps),
            'is_correct': eval_ok,
            'eff': round(eff, 4),
            'waste': round(waste, 4),
            'group': group,
        })

    total_common = len(task_results)
    eval_success = sum(1 for t in task_results if t['is_correct'])
    eval_fail_count = total_common - eval_success

    # Summary metrics
    avg_sr = (eval_success / total_common) if total_common > 0 else 0.0
    avg_eff = (sum(t['eff'] for t in task_results) / eval_success) if eval_success > 0 else 0.0
    avg_waste = (sum(t['waste'] for t in task_results) / eval_fail_count) if eval_fail_count > 0 else 0.0
    avg_spl = (sum(t['eff'] for t in task_results) / total_common) if total_common > 0 else 0.0

    # Group-level SPL and SR (L1=Short, L2=Long)
    level_spl = {}
    level_sr = {}
    for level, groups in [('L1', ['Short', 'Medium']), ('L2', ['Long'])]:
        level_tasks = [t for t in task_results if t['group'] in groups]
        if level_tasks:
            level_spl[level] = round(sum(t['eff'] for t in level_tasks) / len(level_tasks), 4)
            level_success = sum(1 for t in level_tasks if t['is_correct'])
            level_sr[level] = round(level_success / len(level_tasks), 4)
        else:
            level_spl[level] = None
            level_sr[level] = None

    output = {
        'summary': {
            'total_tasks': total_common,
            'success_count': eval_success,
            'fail_count': eval_fail_count,
            'sr': round(avg_sr, 4),
            'efficiency': round(avg_eff, 4),
            'waste': round(avg_waste, 4),
            'spl': round(avg_spl, 4),
            'spl_L1': level_spl.get('L1'),
            'spl_L2': level_spl.get('L2'),
            'sr_L1': level_sr.get('L1'),
            'sr_L2': level_sr.get('L2'),
        },
        'only_in_ref': only_ref,
        'only_in_eval': only_eval,
        'tasks': task_results,
    }

    output_dir = os.path.dirname(os.path.abspath(output_file))
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'Report saved to: {output_file}')


def main():
    parser = argparse.ArgumentParser(
        description="Calculate SR, SPL, IE metrics from two JSON files"
    )
    parser.add_argument(
        '--ref',
        type=str,
        required=True,
        help='Path to the reference (human) JSON file produced by eval_checkpoint.py',
    )
    parser.add_argument(
        '--eval',
        type=str,
        required=True,
        help='Path to the evaluation JSON file produced by eval_checkpoint.py',
    )
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Path to the output JSON file',
    )
    args = parser.parse_args()

    for path, name in [(args.ref, 'ref'), (args.eval, 'eval')]:
        if not os.path.exists(path):
            print(f'Error: File not found ({name}): {path}')
            return 1

    with open(args.ref, 'r', encoding='utf-8') as f:
        ref_data = json.load(f)

    with open(args.eval, 'r', encoding='utf-8') as f:
        eval_data = json.load(f)

    compare_steps(ref_data, eval_data, args.output)


if __name__ == '__main__':
    exit(main())