#!/usr/bin/env python3
"""Extract checkpoint results from a checkpoint directory into a JSON file.

Usage:
    python eval_checkpoint.py --checkpoint_dir <dir> --output <output_file>
"""

import argparse
import gzip
import json
import math
import os
import pickle
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


def load_episode_map(checkpoint_dir):
    """Read all pkl.gz files in a checkpoint directory and extract task info."""
    files = sorted([f for f in os.listdir(checkpoint_dir) if f.endswith('.pkl.gz')])
    result = {}
    for filename in files:
        filepath = os.path.join(checkpoint_dir, filename)
        try:
            with gzip.open(filepath, 'rb') as f:
                data = pickle.load(f)
        except Exception as e:
            print(f'Error loading {filename}: {e}')
            continue
        if isinstance(data, list) and data:
            match = GROUP_PATTERN.search(filename)
            group = match.group(1) if match else 'Other'
            result[filename] = {
                'task_template': data[0].get('task_template', filename),
                'is_successful': clean_nan(data[0].get('is_successful', None)),
                'episode_length': clean_nan(data[0].get('episode_length', None)),
                'goal': data[0].get('goal', None),
                'group': group,
            }
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Extract checkpoint results into a JSON file"
    )
    parser.add_argument(
        '--checkpoint_dir',
        type=str,
        required=True,
        help='Path to the checkpoint directory containing pkl.gz files',
    )
    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='Path to the output JSON file',
    )
    args = parser.parse_args()

    if not os.path.exists(args.checkpoint_dir):
        print(f'Error: Directory not found: {args.checkpoint_dir}')
        return 1

    episode_map = load_episode_map(args.checkpoint_dir)

    output_dir = os.path.dirname(os.path.abspath(args.output))
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(episode_map, f, ensure_ascii=False, indent=2)

    print(f'Extracted {len(episode_map)} episodes to {args.output}')


if __name__ == '__main__':
    exit(main())