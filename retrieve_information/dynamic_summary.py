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

"""Dynamic summary filter for user history."""

import json
import os
from datetime import datetime
from typing import Any

from retrieve_information.llm import _call_llm
from retrieve_information.llm import ERROR_CALLING_LLM
from retrieve_information.llm import get_token_stats


APP_DESCRIPTION = '''Here are the known apps and their functions:
- simple sms messenger: For sending and receiving SMS messages.
- simple gallery: For browsing and editing images.
- simple calendar: Calendar app, for scheduling and managing events.
- clock: Check time, stopwatch, alarm clock and more.
- broccoli: receipe app, for viewing and edit recipes.
- calculator: Calculator app, for performing calculations.
- simple draw: For drawing.
- files: For file management.
- joplin: Notes app, for managing notes.
- tasks: Used to record to-do items.
- 2048: Game app.
- gauguin: Game app.
- solitairecg : Game app.
- tuantuanwaimai: Food delivery app.
- chilemei: Food delivery app.
- taodian: Online shopping app.
- jingdian: Online shopping app.
- pro expense: A bill recording app for tracking income and expenses.
- retro music: Music player app.
- settings: Used to configure various functions of the mobile phone.
- opentracks: Sports recording app.
- phone: Used to make and receive phone calls.
- contacts: Used to manage phone contacts.
- osmand: Map app.
- markor: Notes app, for managing notes.
- librera fd: Reading app.
- lxreader: Reading app.
- chrome: Web browser app.
- clipper: Clipboard.
- camera: Camera app.
- audio recorder: Audio recorder app.
'''

FILTER_PROMPT_TEMPLATE = (
  "You are a precise context filter for an Android GUI Agent.\n"
  "User Goal: {goal}\n"
  f"{APP_DESCRIPTION}\n"
  "History Summary: {summary}\n"
  "Task: From the History Summary, extract only the specific facts, user inputs, or state information necessary to complete the current Goal. \n"
  "If the history contains no information that directly aids the Goal, return an empty string.\n"
  "Filtered Context:\n"
)


def load_summary_by_goal(goal: str, summary_path: str) -> str:
  """Load summary string matching the given goal from JSON file.

  Args:
    goal: The goal instruction to match against tasks in the summary.
    summary_path: Path to the summary JSON file.

  Returns:
    The matching summary string.

  Raises:
    FileNotFoundError: If summary file does not exist.
    json.JSONDecodeError: If summary file is not valid JSON.
    ValueError: If no matching task found for the goal.
  """
  try:
    with open(summary_path, 'r', encoding='utf-8') as f:
      summaries = json.load(f)
  except FileNotFoundError as e:
    raise FileNotFoundError(f'Summary file not found: {summary_path}') from e
  except json.JSONDecodeError as e:
    raise json.JSONDecodeError(
        f'Invalid JSON in summary file: {summary_path}', e.doc, e.pos
    ) from e

  for item in summaries:
    tasks = item.get('tasks', [])
    for task in tasks:
      if task == goal:
        # Check if item contains error_batch_id (top-level field)
        if 'error_batch_id' in item:
          raise ValueError(
              f'Summary contains error_batch_id for goal: {goal}'
          )
        if 'summary' not in item:
          raise ValueError(
              f'Summary field missing for goal: {goal}'
          )
        return item['summary']

  raise ValueError(
      f'No matching task found in summary file "{summary_path}" for goal: {goal}'
  )


def get_filtered_history(goal: str, summary_path: str, log_path: str | None = None) -> str:
  """Get filtered user history from summary file based on goal.

  Uses LLM to analyze the user's past operation history and extract
  only information relevant to the current goal.

  Args:
    goal: The goal instruction for the agent. Used to filter relevant
      user history from the summary.
    summary_path: Path to the summary JSON file.

  Returns:
    Filtered user history string, or empty string if no relevant info.

  Raises:
    FileNotFoundError: If summary file does not exist.
    json.JSONDecodeError: If summary file is not valid JSON.
    ValueError: If no matching task found for the goal.
    RuntimeError: If LLM call fails.
  """
  # Load the summary for the matching goal
  summary = load_summary_by_goal(goal, summary_path)

  # If summary is empty, return empty string
  if not summary.strip():
    return ''

  # Build prompt for LLM to filter relevant information
  prompt = FILTER_PROMPT_TEMPLATE.format(
      goal=goal,
      summary=summary,
  )

  # Call LLM to filter relevant information
  response = _call_llm(prompt)

  if response == ERROR_CALLING_LLM:
    raise RuntimeError(
        f'LLM call failed when filtering history for goal: {goal}'
    )

  # Check if no relevant info
  if '<NO_RELEVANT_INFO>' in response or not response.strip():
    user_history = ''
    print(f"[DEBUG] Empty response for goal: {goal[:50]}...")
    print(f"[DEBUG] response repr: {repr(response)}")
  else:
    user_history = response.strip()

  # Log to file
  log_entries = []
  log_entries.append(f"=== Dynamic Summary Log ===")
  log_entries.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
  log_entries.append(f"Goal: {goal}")
  log_entries.append(f"user_history: {user_history}")

  # Token statistics
  input_tokens, output_tokens = get_token_stats()
  total_tokens = input_tokens + output_tokens
  log_entries.append(f"Token stats - Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}")
  log_entries.append("=" * 50)
  log_entries.append("")

  # Write to log file
  if log_path:
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, 'a', encoding='utf-8') as f:
      f.write('\n'.join(log_entries))

  return user_history


def get_all_history(goal: str, summary_path: str) -> str:
  """Get user history for the matching goal from summary file.

  Args:
    goal: The goal instruction for the agent. Used to find matching history.
    summary_path: Path to the summary JSON file.

  Returns:
    Summary string for the matching goal.

  Raises:
    FileNotFoundError: If summary file does not exist.
    json.JSONDecodeError: If summary file is not valid JSON.
    ValueError: If no matching task found for the goal.
  """
  return load_summary_by_goal(goal, summary_path)
