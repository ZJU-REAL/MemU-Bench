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

"""Memory filter for user history."""

import json
import os
import re
from datetime import datetime
from typing import List

from retrieve_information.llm import _call_llm
from retrieve_information.llm import ERROR_CALLING_LLM
from retrieve_information.llm import get_token_stats

APP_DESCRIPTION = {
    'simple sms messenger': 'For sending and receiving SMS messages.',
    'simple gallery': 'For browsing and editing images.',
    'simple calendar': 'Calendar app, for scheduling and managing events.',
    'clock': 'Check time, stopwatch, alarm clock and more.',
    'broccoli': 'receipe app, for viewing and edit recipes.',
    'calculator': 'Calculator app, for performing calculations.',
    'simple draw': 'For drawing.',
    'files': 'For file management.',
    'joplin': 'Notes app, for managing notes.',
    'tasks': 'Used to record to-do items.',
    '2048': 'Game app.',
    'gauguin': 'Game app.',
    'solitairecg': 'Game app.',
    'tuantuanwaimai': 'Food delivery app.',
    'chilemei': 'Food delivery app.',
    'taodian': 'Online shopping app.',
    'jingdian': 'Online shopping app.',
    'pro expense': 'A bill recording app for tracking income and expenses.',
    'retro music': 'Music player app.',
    'settings': 'Used to configure various functions of the mobile phone.',
    'opentracks': 'Sports recording app.',
    'phone': 'Used to make and receive phone calls.',
    'contacts': 'Used to manage phone contacts.',
    'osmand': 'Map app.',
    'markor': 'Notes app, for managing notes.',
    'librera fd': 'Reading app.',
    'lxreader': 'Reading app.',
    'chrome': 'Web browser app.',
    'clipper': 'Clipboard.',
    'camera': 'Camera app.',
    'audio recorder': 'Audio recorder app.',
}


def _build_retrieve_prompt(goal: str, apps: set, missing_info: str = None) -> str:
  """Build the retrieve app prompt with dynamic app list."""
  lines = ['Here are the known apps and their functions:']
  for app, desc in APP_DESCRIPTION.items():
    if app.lower() in apps:
      lines.append(f'- {app}: {desc}')

  app_desc = '\n'.join(lines)

  missing_section = ""
  if missing_info:
    missing_section = f"\nThe following information is still missing:\n{missing_info}\n"

  return (
    "You are an agent skilled at analyzing user goals and identifying missing information.\n"
    f"Given the user's goal: {goal}\n"
    f"{app_desc}\n"
    f"{missing_section}"
    "Which apps might contain useful information for completing this goal? Only return apps from the list above.\n"
    "Return the app names in the following format:\n"
    "app 1: <app_name_1>\n"
    "app 2: <app_name_2>\n"
    "...\n"
    "You MUST return at least one app that you think might contain useful information."
  )

CHECK_COMPLETE_PROMPT = """You are evaluating whether the retrieved information is sufficient for an Android phone agent to complete a user's goal. The agent can interact with the phone's UI (tap, swipe, type, search within apps, etc.).

**What the agent can do on its own (does NOT need from memory):**
- Open apps by name
- Search for contacts or items by name within apps
- Navigate UI elements and select items by visible text
- Perform standard app operations

**What the agent DOES need from memory (information it cannot directly discover through UI):**
- Specific data values that must be recalled exactly (codes, passwords, amounts, etc.)
- Content the user previously saw or entered that is no longer on screen
- Cross-app facts that the agent cannot infer without prior context

Given the user's goal: {goal}

And the following retrieved information:
{retrieved_info}

Determine if the retrieved information provides the data the agent needs, or if critical information is still missing.
Be conservative: if the goal only requires actions the agent can perform through UI interaction, and no specific data values are needed from memory, mark as sufficient.

Return your answer in the following format:
sufficient: yes/no
missing information: <describe what specific data is still missing, if any. Only list information the agent truly cannot obtain through UI interaction.>
"""

MAX_RETRIEVE_ITERATIONS = 3

EXTRACT_PROMPT = """You are a precise context filter for an Android GUI Agent.
Given the user's goal:
{goal}

{missing_info}

And the following potentialy useful memory items (in JSON format):
{memory_json}

Extract the information that is useful for completing this goal.
Return a concise description of the relevant information.
This subsequent information will serve as supplementary content to accomplish this goal.
If the history contains no information that directly aids the Goal, return an empty string.\n
"""


def load_memory_by_goal(goal: str, memory_path: str) -> list:
  """Load memory list for the matching goal from memory file.

  Args:
    goal: The goal instruction for the agent. Used to find matching history.
    memory_path: Path to the memory JSON file.

  Returns:
    List of memory items for the matching goal.

  Raises:
    FileNotFoundError: If memory file does not exist.
    json.JSONDecodeError: If memory file is not valid JSON.
    ValueError: If no matching task found for the goal.
  """
  try:
    with open(memory_path, 'r', encoding='utf-8') as f:
      memory_data = json.load(f)
  except FileNotFoundError as e:
    raise FileNotFoundError(f'Memory file not found: {memory_path}') from e
  except json.JSONDecodeError as e:
    raise json.JSONDecodeError(
        f'Invalid JSON in memory file: {memory_path}', e.doc, e.pos
    ) from e

  for item in memory_data:
    tasks = item.get('tasks', [])
    for task in tasks:
      if task == goal:
        # Check if item contains error_batch_id (top-level field)
        if 'error_batch_id' in item:
          raise ValueError(
              f'Memory contains error_batch_id for goal: {goal}'
          )
        if 'memory' not in item:
          raise ValueError(
              f'Memory field missing for goal: {goal}'
          )
        return item['memory']

  raise ValueError(
      f'No matching task found in memory file "{memory_path}" for goal: {goal}'
  )


def retrieve(memory: list, goal: str, apps: set, missing_info: str = None) -> tuple:
  """Retrieve relevant history from memory based on goal.

  Args:
    memory: List of memory items.
    goal: The goal instruction for the agent. Used to filter relevant
      user history from the memory.
    apps: Set of app names to consider for retrieval.
    missing_info: Information that is still missing from previous retrieval.

  Returns:
    Tuple of (filtered_memory, relevant_apps).
  """
  prompt = _build_retrieve_prompt(goal, apps, missing_info)

  llm_response = _call_llm(prompt)

  # Parse LLM response to get relevant app names
  if llm_response == ERROR_CALLING_LLM:
    return [], set()

  # Extract app names from response
  # Expected format: "app 1: <name>\napp 2: <name>\n..."
  relevant_apps = set()
  for line in llm_response.strip().split('\n'):
    if ':' in line:
      app_name = line.split(':', 1)[1].strip().lower()
      if app_name and app_name != 'none':
        relevant_apps.add(app_name)

  # Filter memory: match case-insensitively
  filtered_memory = [
    m for m in memory
    if m.get('app', '').lower() in relevant_apps
  ]

  return filtered_memory, relevant_apps

def extract(filtered_memory: list, goal: str, missing_info: str = None) -> str:
  """Extract final string information from filtered memory.

  Args:
    filtered_memory: List of filtered memory items.
    goal: The goal instruction for the agent.
    missing_info: Information that is still missing from previous retrieval.

  Returns:
    Formatted string representation of the memory.
  """
  if not filtered_memory:
    return ''

  if missing_info:
    missing_info = f"The following information is still missing:\n{missing_info}"
  else:
    missing_info = ""

  memory_json = json.dumps(filtered_memory, ensure_ascii=False, indent=2)

  prompt = EXTRACT_PROMPT.format(goal=goal, memory_json=memory_json, missing_info=missing_info)

  llm_response = _call_llm(prompt)

  if llm_response == ERROR_CALLING_LLM:
    return ''

  return llm_response

def check_retrieval_complete(goal: str, retrieved_info: str) -> tuple:
  """Check if the retrieved information is sufficient for the goal.

  Args:
    goal: The goal instruction for the agent.
    retrieved_info: The information retrieved so far.

  Returns:
    A tuple of (is_sufficient: bool, missing_info: str)
  """
  if not retrieved_info.strip():
    prompt = CHECK_COMPLETE_PROMPT.format(
        goal=goal, retrieved_info="(No information retrieved yet)"
    )
  else:
    prompt = CHECK_COMPLETE_PROMPT.format(
        goal=goal, retrieved_info=retrieved_info
    )

  llm_response = _call_llm(prompt)

  if llm_response == ERROR_CALLING_LLM:
    return False, "Error calling LLM"

  is_sufficient = False
  missing_info = ""

  # Extract sufficient field
  sufficient_match = re.search(r'sufficient:\s*(yes|no)', llm_response, re.IGNORECASE)
  if sufficient_match:
    is_sufficient = sufficient_match.group(1).lower() == 'yes'

  # Extract missing information (may span multiple lines)
  missing_match = re.search(r'missing information:\s*(.*)', llm_response, re.DOTALL | re.IGNORECASE)
  if missing_match:
    missing_info = missing_match.group(1).strip()

  return is_sufficient, missing_info


def get_filtered_history(goal: str, memory_path: str, max_retrieve_iterations: int = MAX_RETRIEVE_ITERATIONS, log_path: str | None = None) -> str:
  """Get filtered user history from memory file based on goal.

  This function uses iterative retrieval:
  1. First retrieves apps that might contain relevant information
  2. Extracts information from those apps
  3. Checks if the retrieved information is sufficient
  4. If not sufficient, iterates again with potentially new apps

  Args:
    goal: The goal instruction for the agent. Used to filter relevant
      user history from the memory.
    memory_path: Path to the memory JSON file.
    max_retrieve_iterations: Maximum number of retrieval iterations.

  Returns:
    Filtered user history data.

  Raises:
    FileNotFoundError: If memory file does not exist.
    json.JSONDecodeError: If memory file is not valid JSON.
    ValueError: If no matching task found for the goal.
  """
  log_entries = []
  log_entries.append(f"=== Memory Retrieval Log ===")
  log_entries.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
  log_entries.append(f"Goal: {goal}")
  log_entries.append("")

  memory_list = load_memory_by_goal(goal, memory_path)
  available_apps = set(m.get('app', '').lower() for m in memory_list if m.get('app')) & set(APP_DESCRIPTION.keys())
  all_retrieved_info = ""
  previously_retrieved_apps = set()
  missing_info = None

  for iteration in range(max_retrieve_iterations):
    remaining_apps = available_apps - previously_retrieved_apps
    if not remaining_apps:
      log_entries.append(f"[Iteration {iteration + 1}] No more apps to retrieve")
      print(f"[Iteration {iteration + 1}] No more apps to retrieve")
      break

    log_entries.append(f"[Iteration {iteration + 1}] Remaining apps: {remaining_apps}")
    print(f"[Iteration {iteration + 1}] Remaining apps: {remaining_apps}")

    filtered_memory, current_apps = retrieve(memory_list, goal, remaining_apps, missing_info)
    log_entries.append(f"[Iteration {iteration + 1}] Retrieved apps: {current_apps}")
    print(f"[Iteration {iteration + 1}] Retrieved apps: {current_apps}")
    previously_retrieved_apps.update(current_apps)

    extracted_info = extract(filtered_memory, goal, missing_info)
    log_entries.append(f"[Iteration {iteration + 1}] Extracted info: {extracted_info if extracted_info else '(empty)'}...")
    print(f"[Iteration {iteration + 1}] Extracted info: {extracted_info if extracted_info else '(empty)'}...")
    if extracted_info:
      all_retrieved_info += extracted_info + "\n"

    if max_retrieve_iterations > 1:
      log_entries.append(f"[Iteration {iteration + 1}] Checking if sufficient")
      print(f"[Iteration {iteration + 1}] Checking if sufficient")
      # Check if we have enough information
      is_sufficient, missing_info = check_retrieval_complete(
          goal, all_retrieved_info
      )
      log_entries.append(f"[Iteration {iteration + 1}] Is sufficient: {is_sufficient}, Missing info: {missing_info}")
      print(f"[Iteration {iteration + 1}] Is sufficient: {is_sufficient}, Missing info: {missing_info}")
      if is_sufficient:
        break

  log_entries.append("")
  log_entries.append(f"Final user_history: {all_retrieved_info}")

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

  return all_retrieved_info


def get_all_history(goal: str, memory_path: str) -> str:
  """Get user history for the matching goal from memory file.

  Args:
    goal: The goal instruction for the agent. Used to find matching history.
    memory_path: Path to the memory JSON file.

  Returns:
    Concatenated event strings from memory for the matching goal.

  Raises:
    FileNotFoundError: If memory file does not exist.
    json.JSONDecodeError: If memory file is not valid JSON.
    ValueError: If no matching task found for the goal.
  """
  memory_list = load_memory_by_goal(goal, memory_path)
  parts = []
  for i, m in enumerate(memory_list, 1):
    event = m.get('event', '')
    details = m.get('details', '')
    parts.append(f'Event{i}: {event}\nDetails: {details}')
  return '\n'.join(parts)
