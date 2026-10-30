"""Standalone script to generate user_history for each task and save to JSON.

Iterates over all tasks in the user information JSON file, calls the
filtering/retrieval function for each task, and saves the results
(goal, user_history, token cost) to an output JSON file.

Usage:
  python -m retrieve_information.retrieve_information \
      --method dynamic_summary \
      --path /path/to/user_information/summary/Qwen3.5-397B-A17B.json \
      --output /path/to/output.json

  python -m retrieve_information.retrieve_information \
      --method memory \
      --path /path/to/user_information/memory/Qwen3.5-397B-A17B.json \
      --output /path/to/output.json
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Ensure project root is on sys.path so imports work when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from retrieve_information import get_filtered_user_history
from retrieve_information.llm import get_token_stats, reset_token_stats


def load_goals_from_file(path: str) -> list[dict]:
    """Extract all unique task goals with subdir from a user information JSON file.

    Args:
        path: Path to the JSON file (summary or memory format).

    Returns:
        List of dicts with 'goal' and 'subdir' keys.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    goals = []
    seen = set()
    for item in data:
        subdir = item.get("subdir", "")
        for task in item.get("tasks", []):
            if task not in seen:
                goals.append({"goal": task, "subdir": subdir})
                seen.add(task)
    return goals


def _process_one(
    task_info: dict,
    method: str,
    path: str,
    filter_user_history: bool,
    max_retrieve_iterations: int,
    log_path: str | None,
) -> dict:
    """Process a single task. Returns a result dict."""
    goal = task_info["goal"]
    subdir = task_info["subdir"]

    reset_token_stats()

    try:
        if filter_user_history:
            user_history = get_filtered_user_history(
                goal, method, path,
                max_retrieve_iterations=max_retrieve_iterations,
                log_path=log_path,
            )
        else:
            raise ValueError("filter_user_history == False is not supported")
    except Exception as e:
        return {
            "goal": goal,
            "subdir": subdir,
            "user_history": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "error": str(e),
        }

    input_tokens, output_tokens = get_token_stats()
    return {
        "goal": goal,
        "subdir": subdir,
        "user_history": user_history,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def generate(
    path: str,
    method: str,
    output_path: str,
    filter_user_history: bool = True,
    max_retrieve_iterations: int = 3,
    log_path: str | None = None,
    workers: int = 4,
) -> None:
    """Generate user_history for every task and write results to JSON.

    Args:
        path: Path to the user information JSON file.
        method: Method name (dynamic_summary, memory, without_history).
        output_path: Where to write the output JSON.
        filter_user_history: If True use get_filtered_user_history,
            otherwise get_all_user_history.
        max_retrieve_iterations: Maximum number of retrieval iterations
            for the memory method.
        log_path: Path to the log file. If None, no log is written.
        workers: Number of concurrent threads.
    """
    goals = load_goals_from_file(path)
    print(f"Found {len(goals)} tasks in {path}")

    # Load existing results if resuming
    existing_results = []
    processed_goals = set()

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            existing_results = existing.get("results", [])
            # Remove error results so they get reprocessed
            existing_results = [r for r in existing_results if "error" not in r]
            processed_goals = {r["goal"] for r in existing_results}
            print(f"Resuming from {len(existing_results)} existing results")
        except (json.JSONDecodeError, KeyError):
            print(f"Could not parse existing output file, starting fresh")

    # Filter out already-processed items
    pending = []
    for i, task_info in enumerate(goals, 1):
        if task_info["goal"] in processed_goals:
            print(f"[{i}/{len(goals)}] Skipping (already processed): {task_info['goal'][:80]}...")
        else:
            pending.append(task_info)

    if not pending:
        print("All items already processed.")
        return

    print(f"Pending: {len(pending)}/{len(goals)} items to process (workers={workers})")

    lock = Lock()
    new_results = []
    done_count = 0

    def _save_results():
        output = {
            "model": os.environ.get('MODEL', ''),
            "method": method,
            "source_path": path,
            "filter_user_history": filter_user_history,
            "max_retrieve_iterations": max_retrieve_iterations if method == "memory" else None,
            "total_tasks": len(goals),
            "results": existing_results + new_results,
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_task = {
            executor.submit(
                _process_one, task_info, method, path,
                filter_user_history, max_retrieve_iterations, log_path,
            ): task_info
            for task_info in pending
        }

        for future in as_completed(future_to_task):
            task_info = future_to_task[future]
            try:
                result = future.result()
            except Exception as e:
                result = {
                    "goal": task_info["goal"],
                    "subdir": task_info["subdir"],
                    "user_history": "",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "error": str(e),
                }

            with lock:
                done_count += 1
                new_results.append(result)

                if "error" in result:
                    print(f"[{done_count}/{len(pending)}] ERROR: {result['goal'][:80]}... ({result['error']})")
                else:
                    print(f"[{done_count}/{len(pending)}] Done: {result['goal'][:80]}... (in={result['input_tokens']}, out={result['output_tokens']})")

                _save_results()

    # Reload final results count from the saved file
    with open(output_path, "r", encoding="utf-8") as f:
        final_data = json.load(f)
    final_count = len(final_data.get("results", []))
    print(f"\nDone. Results saved to {output_path}")
    print(f"Total: {len(goals)} tasks, {final_count} results")


def main():
    parser = argparse.ArgumentParser(
        description="Generate user_history for each task and save to JSON"
    )
    parser.add_argument(
        "--method",
        type=str,
        required=True,
        choices=["dynamic_summary", "memory", "without_history", "memory_rag", "summary_rag"],
        help="Method for processing user history",
    )
    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="Path to the user information JSON file",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON path (default: same dir as source, named <method>_result.json)",
    )
    parser.add_argument(
        "--no_filter",
        action="store_true",
        help="Use get_all_user_history instead of get_filtered_user_history",
    )
    parser.add_argument(
        "--max_retrieve_iterations",
        type=int,
        default=3,
        help="Maximum number of retrieval iterations for the memory method (default: 3)",
    )
    parser.add_argument(
        "--log_path",
        type=str,
        default=None,
        help="Path to the log file. If not set, no log is written.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of concurrent threads (default: 4, use 1 for per-task token tracking)",
    )
    parser.add_argument(
        "--env_file",
        type=str,
        default=".env",
        help="Path to the environment variables file. Defaults to .env",
    )
    args = parser.parse_args()

    # Load environment variables from specified env file
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), args.env_file)
    if os.path.isfile(env_path):
        load_dotenv(env_path, override=True)
        print(f"Loaded environment variables from {env_path}")
    else:
        # Fallback to default .env in project root
        default_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
        if os.path.isfile(default_env_path):
            load_dotenv(default_env_path, override=True)
            print(f"Warning: {env_path} not found, loaded default {default_env_path}")
        else:
            print(f"Warning: Env file not found: {env_path} or {default_env_path}, using system environment variables")

    if args.method == "without_history":
        print("Method is 'without_history' — nothing to generate.")
        return

    output_path = args.output
    if output_path is None:
        base_dir = os.path.dirname(args.path)
        output_path = os.path.join(base_dir, f"{args.method}_result.json")

    generate(
        path=args.path,
        method=args.method,
        output_path=output_path,
        filter_user_history=not args.no_filter,
        max_retrieve_iterations=args.max_retrieve_iterations,
        log_path=args.log_path,
        workers=args.workers,
    )


if __name__ == "__main__":
    main()
