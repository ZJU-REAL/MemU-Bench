#!/usr/bin/env python3
# Copyright 2026 The android_world Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Command-line interface for log summarization with task mapping.

This script provides a CLI for summarizing user operation logs
using different LLM models, and directly adds task mapping to the output.
"""

import argparse
import json
import os
import sys
from typing import Any

# Add project root to path for proper import (must be before importing memory_generation)
current_file = os.path.abspath(__file__)
# Go up 3 levels: dynamic_summary -> memory_generation -> echonav
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
sys.path.insert(0, project_root)

from memory_generation.dynamic_summary.base import BaseSummarizer
from dotenv import load_dotenv

# Load task mapping from tasks_map.json
_tasks_map_path = os.path.join(os.path.dirname(current_file), '..', 'tasks_map.json')
with open(_tasks_map_path, 'r', encoding='utf-8') as _f:
    SESSION_TO_TASK = json.load(_f)

# 获取当前文件所在的目录
current_dir = os.path.dirname(current_file)
# 获取当前文件的上级目录 (新增一步)
processed_data_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), "processed_data")
# 拼接上级目录下的 raw_history 文件夹
DEFAULT_OUTPUT_DIR = os.path.join(processed_data_dir, "summary")


def get_model_from_env() -> str:
    """Get model name from environment variable."""
    return os.environ.get('MODEL', '')



def add_task_to_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Add task attribute to a summary entry.

    Args:
        summary: A summary dictionary with user and subdir.

    Returns:
        Summary dictionary with task attribute added.
    """
    user = summary.get("user", "")
    subdir = summary.get("subdir", "")
    tasks = SESSION_TO_TASK.get(user, {}).get(subdir, [])

    result = summary.copy()
    result["tasks"] = tasks
    return result


def summarize_session(
    session_path: str,
    batch_size: int = 10,
    verbose: bool = True,
    user: str = '',
    subdir: str = '',
    calc_token: bool = False,
    **kwargs,
) -> dict[str, Any]:
    """Summarize a recording session and add task mapping.

    Args:
        session_path: Path to session directory or processed.jsonl file.
        batch_size: Number of screenshots to process per batch.
        verbose: Whether to print progress information.
        user: The user identifier (e.g., 'user1').
        subdir: The subdirectory name (e.g., 'short').
        calc_token: Whether to track per-batch input/output token counts.
        **kwargs: Additional arguments passed to the summarizer.

    Returns:
        Dict containing summary, metadata, and task.
    """
    # Determine log path
    if os.path.isfile(session_path):
        log_path = session_path
    else:
        log_path = os.path.join(session_path, 'processed.jsonl')

    if not os.path.exists(log_path):
        raise FileNotFoundError(f"Log file not found: {log_path}")

    # Use model from environment variable
    model_name = get_model_from_env()
    summarizer = BaseSummarizer(model_name=model_name, **kwargs)
    summary_result = summarizer.summarize_log(log_path, batch_size=batch_size, verbose=verbose, calc_token=calc_token)

    # Build result with user, subdir and summary
    result = {
        "user": user,
        "subdir": subdir,
        "summary": summary_result.get("summary", ""),
        "metadata": {
            "session_path": session_path,
            "model": model_name,
            "batch_size": batch_size,
        }
    }

    # Add error_batch_id if present (only when there's an error)
    if "error_batch_id" in summary_result:
        result["error_batch_id"] = summary_result["error_batch_id"]

    # Add per-round token lists if present
    if "input_tokens" in summary_result:
        result["input_tokens"] = summary_result["input_tokens"]
    if "output_tokens" in summary_result:
        result["output_tokens"] = summary_result["output_tokens"]

    # Add task mapping directly
    result = add_task_to_summary(result)

    return result


def summarize_sessions(
    session_paths: list[str],
    batch_size: int = 10,
    verbose: bool = True,
    output_path: str = '',
    calc_token: bool = False,
    **kwargs,
) -> list[dict[str, Any]]:
    """Summarize multiple recording sessions and save to a JSON file with task mapping.

    Args:
        session_paths: List of paths to session directories or processed.jsonl files.
        batch_size: Number of screenshots to process per batch.
        verbose: Whether to print progress information.
        output_path: Path to the output JSON file.
        calc_token: Whether to track per-batch input/output token counts.
        **kwargs: Additional arguments passed to the summarizer.

    Returns:
        List of dicts containing summary, metadata, and tasks for each session.
    """
    if not output_path:
        model_name = get_model_from_env()
        output_path = os.path.join(DEFAULT_OUTPUT_DIR, f"{model_name.replace('/', '_')}.json")
    all_results = {}  # "user_subdir" -> result

    # Load existing results if file exists
    if os.path.exists(output_path):
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                for item in existing_data:
                    key = f"{item.get('user', '')}_{item.get('subdir', '')}"
                    if key:
                        all_results[key] = item
            if verbose:
                print(f"Loaded {len(all_results)} existing results from {output_path}")
        except Exception as e:
            if verbose:
                print(f"Warning: Could not load existing results: {e}")

    def save_results():
        """Helper function to save results to JSON file."""
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        results_list = list(all_results.values())
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results_list, f, ensure_ascii=False, indent=2)
        if verbose:
            print(f"\n{'='*60}")
            print(f"Saved {len(results_list)} summaries with tasks to: {output_path}")
            print(f"{'='*60}")

    for i, session_path in enumerate(session_paths):
        if verbose:
            print(f"\n[{i+1}/{len(session_paths)}] Processing: {session_path}")

        # Extract user and subdir from path
        # Path: .../user1/short -> user="user1", subdir="short"
        if os.path.isdir(session_path):
            subdir = os.path.basename(session_path)
            user = os.path.basename(os.path.dirname(session_path))
        else:
            # If session_path is a file, get parent directories
            subdir = os.path.basename(os.path.dirname(session_path))
            user = os.path.basename(os.path.dirname(os.path.dirname(session_path)))
        dedup_key = f"{user}_{subdir}"

        # Check if session already exists and is complete (no error_batch_id)
        model_name = get_model_from_env()
        if dedup_key in all_results:
            existing = all_results[dedup_key]
            if 'error_batch_id' not in existing:
                # Check if model matches
                if existing.get('metadata', {}).get('model') != model_name:
                    if verbose:
                        print(f"  Session '{dedup_key}' model mismatch (existing: {existing.get('metadata', {}).get('model')}, current: {model_name}), reprocessing...")
                else:
                    # Check if tasks field matches the predefined mapping
                    expected_tasks = SESSION_TO_TASK.get(user, {}).get(subdir, [])
                    existing_tasks = existing.get('tasks', [])
                    if existing_tasks != expected_tasks:
                        if verbose:
                            print(f"  Session '{dedup_key}' tasks mismatch, updating tasks field...")
                        existing['tasks'] = expected_tasks
                        all_results[dedup_key] = existing
                        save_results()
                    if verbose:
                        print(f"  Session '{dedup_key}' already processed successfully, skipping...")
                    continue
            else:
                # Has error_batch_id, need to resume from failed batch
                error_batch_id = existing['error_batch_id']
                previous_summary = existing.get('summary', '')
                previous_input_tokens = existing.get('input_tokens')
                previous_output_tokens = existing.get('output_tokens')
                if verbose:
                    print(f"  Session '{dedup_key}' has error at batch {error_batch_id}, resuming...")
                    print(f"  Loaded previous summary: {previous_summary[:200]}...")
                try:
                    result = summarize_session_resume(
                        session_path,
                        batch_size=batch_size,
                        start_batch=error_batch_id,
                        previous_summary=previous_summary,
                        verbose=verbose,
                        user=user,
                        subdir=subdir,
                        calc_token=calc_token,
                        previous_input_tokens=previous_input_tokens,
                        previous_output_tokens=previous_output_tokens,
                        **kwargs,
                    )
                    all_results[dedup_key] = result
                    save_results()
                except FileNotFoundError as e:
                    print(f"  Skipping: {e}")
                    continue
                except Exception as e:
                    print(f"  Error processing {session_path}: {e}")
                    raise
                continue

        try:
            result = summarize_session(
                session_path,
                batch_size=batch_size,
                verbose=verbose,
                user=user,
                subdir=subdir,
                calc_token=calc_token,
                **kwargs,
            )
            all_results[dedup_key] = result
            save_results()
        except FileNotFoundError as e:
            print(f"  Skipping: {e}")
            continue
        except Exception as e:
            print(f"  Error processing {session_path}: {e}")
            raise  # Re-raise to stop processing

    return list(all_results.values())


def summarize_session_resume(
    session_path: str,
    batch_size: int = 10,
    start_batch: int = 1,
    previous_summary: str = '',
    verbose: bool = True,
    user: str = '',
    subdir: str = '',
    calc_token: bool = False,
    previous_input_tokens: list[int] | None = None,
    previous_output_tokens: list[int] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """Resume summarizing a session from a failed batch.

    Args:
        session_path: Path to session directory or processed.jsonl file.
        batch_size: Number of screenshots to process per batch.
        start_batch: The batch number to resume from (after the failed batch).
        previous_summary: The summary from previous batches before the error.
        verbose: Whether to print progress information.
        session_name: The session folder name for this session.
        user: The user identifier (e.g., 'user1').
        subdir: The subdirectory name (e.g., 'short').
        calc_token: Whether to track per-batch input/output token counts.
        previous_input_tokens: Token list from batches before the error.
        previous_output_tokens: Token list from batches before the error.
        **kwargs: Additional arguments passed to the summarizer.

    Returns:
        Dict containing summary, metadata, and task.
    """
    # Determine log path
    if os.path.isfile(session_path):
        log_path = session_path
    else:
        log_path = os.path.join(session_path, 'processed.jsonl')

    if not os.path.exists(log_path):
        raise FileNotFoundError(f"Log file not found: {log_path}")

    # Use model from environment variable
    model_name = get_model_from_env()
    summarizer = BaseSummarizer(model_name=model_name, **kwargs)

    summary_result = summarizer.summarize_log_from_batch(
        log_path,
        batch_size=batch_size,
        start_batch=start_batch,
        previous_summary=previous_summary,
        verbose=verbose,
        calc_token=calc_token,
    )

    # Build result with user, subdir and summary
    result = {
        "user": user,
        "subdir": subdir,
        "summary": summary_result.get("summary", ""),
        "metadata": {
            "session_path": session_path,
            "model": model_name,
            "batch_size": batch_size,
            "resumed_from_batch": start_batch,
        }
    }

    # Add error_batch_id if present (only when there's an error)
    if "error_batch_id" in summary_result:
        result["error_batch_id"] = summary_result["error_batch_id"]

    # Merge previous token lists with new ones from resumed batches
    if "input_tokens" in summary_result or previous_input_tokens:
        result["input_tokens"] = (previous_input_tokens or []) + summary_result.get("input_tokens", [])
    if "output_tokens" in summary_result or previous_output_tokens:
        result["output_tokens"] = (previous_output_tokens or []) + summary_result.get("output_tokens", [])

    # Add task mapping directly
    result = add_task_to_summary(result)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Summarize user operation logs using LLM and add task mapping"
    )
    parser.add_argument(
        "--session_paths",
        nargs='+',
        help="Path(s) to session directory(ies) or processed.jsonl file(s). "
             "Can also pass a parent directory containing multiple sessions."
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=10,
        help="Number of screenshots per batch"
    )
    parser.add_argument(
        "--max_retry",
        type=int,
        default=3,
        help="Maximum number of retries on API failure"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress progress output"
    )
    parser.add_argument(
        "-o", "--output_path",
        default='',
        help="Path to the output JSON file (default: <DEFAULT_OUTPUT_DIR>/<model_name>.json)"
    )
    parser.add_argument(
        "--calc_token",
        action="store_true",
        help="Track per-round input/output token counts in the output JSON"
    )
    parser.add_argument(
        "--env_file",
        default='.env',
        help="Path to the environment variables file. Defaults to .env"
    )
    args = parser.parse_args()

    # Load environment variables from specified env file
    env_path = os.path.join(project_root, args.env_file)
    if os.path.isfile(env_path):
        load_dotenv(dotenv_path=env_path, override=True)
        if not args.quiet:
            print(f"Loaded environment variables from {env_path}")
    else:
        # Fallback to default .env in project root
        default_env_path = os.path.join(project_root, '.env')
        if os.path.isfile(default_env_path):
            load_dotenv(dotenv_path=default_env_path, override=True)
            if not args.quiet:
                print(f"Warning: {env_path} not found, loaded default {default_env_path}")
        else:
            if not args.quiet:
                print(f"Warning: Env file not found: {env_path} or {default_env_path}, using system environment variables")

    # Collect all session paths
    session_paths = []

    def find_sessions(root: str):
        """Recursively find directories containing processed.jsonl."""
        for dirpath, _, filenames in os.walk(root):
            if 'processed.jsonl' in filenames:
                session_paths.append(dirpath)

    for path in args.session_paths:
        if os.path.isdir(path):
            find_sessions(path)
        else:
            session_paths.append(path)

    order = {'short': 0, 'medium': 1, 'long': 2}

    def sort_key(p):
        user = os.path.basename(os.path.dirname(p))
        num = int(''.join(filter(str.isdigit, user)) or 0)
        subdir = os.path.basename(p)
        return (num, order.get(subdir, 99))

    session_paths.sort(key=sort_key)

    if not session_paths:
        print("Error: No valid session paths found")
        return 1

    try:
        results = summarize_sessions(
            session_paths,
            batch_size=args.batch_size,
            verbose=not args.quiet,
            output_path=args.output_path,
            calc_token=args.calc_token,
            max_retry=args.max_retry,
        )

        # Print summaries to stdout
        for result in results:
            print("\n" + "=" * 60)
            print(f"Session: {result['metadata']['session_path']}")
            print(f"User: {result['user']}, Subdir: {result['subdir']}")
            print(f"Tasks: {result['tasks']}")
            if 'input_tokens' in result:
                for i, (it, ot) in enumerate(zip(result['input_tokens'], result['output_tokens']), 1):
                    print(f"Round {i}: input_tokens={it}, output_tokens={ot}")
                total_in = sum(result['input_tokens'])
                total_out = sum(result['output_tokens'])
                print(f"Total: input_tokens={total_in}, output_tokens={total_out}")
            print("=" * 60)
            print(result['summary'])

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())