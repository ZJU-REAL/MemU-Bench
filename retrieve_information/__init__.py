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

"""Process user history module."""

from typing import Any

from retrieve_information import dynamic_summary, memory, rag_retrieve, summary_rag_retrieve

# from retrieve_information import w_o_sv as memory

def get_filtered_user_history(
    goal: str,
    method: str,
    path: str | None = None,
    max_retrieve_iterations: int = 3,
    log_path: str | None = None,
) -> str:
  """Get filtered user history based on the goal and method.

  Args:
    goal: The goal instruction for the agent. Used to filter relevant
      user history.
    method: The method to use for filtering. Supported: dynamic_summary,
      memory, without_history.
    path: Path to the JSON file. Required when method is dynamic_summary
      (summary file) or memory (memory file).
    max_retrieve_iterations: Maximum number of retrieval iterations for
      the memory method.
    log_path: Path to the log file. If None, no log is written.

  Returns:
    Filtered user history data, or None if no filtering is needed.

  Raises:
    ValueError: If method is not supported or required path is not provided.
  """
  if method == 'human_count_step':
    return ''
  elif method == 'without_history':
    return ''
  elif method == 'dynamic_summary':
    if path is None:
      raise ValueError(
          'path is required when method is dynamic_summary'
      )
    return dynamic_summary.get_filtered_history(goal, path, log_path=log_path)
  elif method == 'memory':
    if path is None:
      raise ValueError(
          'path is required when method is memory'
      )
    return memory.get_filtered_history(goal, path, max_retrieve_iterations=max_retrieve_iterations, log_path=log_path)
  elif method == 'memory_rag':
    if path is None:
      raise ValueError(
          'path is required when method is memory_rag'
      )
    return rag_retrieve.get_filtered_history(goal, path)
  elif method == 'summary_rag':
    if path is None:
      raise ValueError(
          'path is required when method is summary_rag'
      )
    return summary_rag_retrieve.get_filtered_history(goal, path)
  else:
    raise ValueError(f'Unknown method: {method}')


# def get_all_user_history(
#     goal: str,
#     method: str,
#     path: str | None = None,
# ) -> str:
#   """Get all user history (without filtering) based on the goal and method.

#   Args:
#     goal: The goal instruction for the agent.
#     method: The method to use. Supported: dynamic_summary, memory, without_history.
#     path: Path to the JSON file. Required when method is dynamic_summary
#       (summary file) or memory (memory file).

#   Returns:
#     All user history data.

#   Raises:
#     ValueError: If method is not supported or required path is not provided.
#   """
#   if method == 'human_count_step':
#     return ''
#   elif method == 'without_history':
#     return ''
#   elif method == 'dynamic_summary':
#     if path is None:
#       raise ValueError(
#           'path is required when method is dynamic_summary'
#       )
#     return dynamic_summary.get_all_history(goal, path)
#   elif method == 'memory':
#     if path is None:
#       raise ValueError(
#           'path is required when method is memory'
#       )
#     return memory.get_all_history(goal, path)
#   elif method == 'memory_rag':
#     if path is None:
#       raise ValueError(
#           'path is required when method is memory_rag'
#       )
#     return rag_retrieve.get_all_history(goal, path)
#   else:
#     raise ValueError(f'Unknown method: {method}')
