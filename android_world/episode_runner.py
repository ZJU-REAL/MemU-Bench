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

"""Runs an agent on the environment."""

import dataclasses
import json
import os
from typing import Any, Callable, Optional
from android_world import constants
from android_world.agents import base_agent
from android_world.env import interface
import termcolor
from PIL import Image


@dataclasses.dataclass()
class EpisodeResult:
  """Represents an episode of an agent interacting with the environment.

  Attributes:
    done: Whether the agent indicated the task is complete.
    step_data: Environment and agent data for each step.
    env_reward: Reward returned by environment, if applicable.
    aux_data: Additional data from the episode which may be used for metrics.
    user_history: The user history string used during the episode.
  """

  done: bool
  step_data: dict[str, Any]
  env_reward: Optional[float] = None
  aux_data: Optional[dict[str, Any]] = None
  user_history: str = ''


# Cache for the pre-generated user_history JSON data.
_user_history_cache: dict[str, dict[str, str]] = {}


def _load_user_history(path: str) -> dict[str, str]:
  """Load pre-generated user_history JSON and index by goal.

  Args:
    path: Path to the pre-generated JSON file (output of
      generate_user_history.py).

  Returns:
    Dict mapping goal string to user_history string.
  """
  if path in _user_history_cache:
    return _user_history_cache[path]

  with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

  goal_to_history = {}
  for item in data.get('results', []):
    goal_to_history[item['goal']] = item['user_history']

  _user_history_cache[path] = goal_to_history
  return goal_to_history


def run_episode(
    goal: str,
    agent: base_agent.EnvironmentInteractingAgent,
    max_n_steps: int = 10,
    start_on_home_screen: bool = False,
    termination_fn: Callable[[interface.AsyncEnv], float] | None = None,
    print_fn: Callable[[str], None] = print,
    path: str | None = None,
    information: str = '',
    ask: bool = False,
    save_img_path: str | None = None,
) -> EpisodeResult:
  """Runs an agent on goal, e.g., "turn off wifi".

  An agent will start from whatever state the provided environment is in and
  run until it determines a task is complete, if the max number of
  steps is reached, of if the termination_fn is True.

  Args:
    goal: The goal instruction for the agent.
    agent: The agent to run on the environment.
    max_n_steps: The max number of steps to allow an agent to run before ending
      an episode.
    start_on_home_screen: Whether to start episode from the home screen or just
      the current screen.
    termination_fn: If provided, a determines whether to terminate an episode.
      For example, for MiniWoB++ tasks, the episode should terminate if there is
      a nonzero reward.
    print_fn: A function to print log messages to the console or logger.
    path: Path to the pre-generated user_history JSON file. If provided,
      user_history for the matching goal will be looked up; otherwise empty.
    information: Additional task information provided to the agent (e.g., for
      ask_user scenarios).
    ask: Whether to enable ask mode in agent.step().
    save_img_path: Path to save the last 15 screenshots during agent inference.
      If None, screenshots will not be saved.

  Returns:
    Data collected during running agent on goal.
  """
  if max_n_steps == 0:
    return EpisodeResult(done=False, step_data={}, user_history='')
  if termination_fn is None:
    termination_fn = lambda env: False

  agent.reset(start_on_home_screen)
  agent.set_max_steps(max_n_steps)

  # Look up pre-generated user_history from JSON file
  user_history = ''
  if path:
    goal_to_history = _load_user_history(path)
    user_history = goal_to_history[goal]
  print(f"user_history: {user_history}")

  output = []
  step_actions = []  # 记录每一步的 action
  if save_img_path:
    os.makedirs(save_img_path, exist_ok=True)

  for step_n in range(max_n_steps):
    result = agent.step(goal, information=information, filtered_user_history=user_history, ask=ask)
    print_fn('Completed step {:d}.'.format(step_n + 1))
    assert constants.STEP_NUMBER not in result.data
    output.append(result.data | {constants.STEP_NUMBER: step_n})

    # 保存截图
    if save_img_path and result.data.get('raw_screenshot') is not None:
      img_filename = f'step_{step_n + 1}.jpg'
      img_path = os.path.join(save_img_path, img_filename)
      img = Image.fromarray(result.data['raw_screenshot'])
      img.save(img_path, format='JPEG')

    # 保存 action 到列表
    action_output = result.data.get('action_output_json')
    if action_output is not None:
      # 将 JSONAction 对象转换为字典
      action_dict = {
        'step': step_n + 1,
        'action_type': getattr(action_output, 'action_type', None),
        'text': getattr(action_output, 'text', None),
        'element': getattr(action_output, 'element', None),
        'goal_status': getattr(action_output, 'goal_status', None),
        'direction': getattr(action_output, 'direction', None),
        'app_name': getattr(action_output, 'app_name', None),
        'x': getattr(action_output, 'x', None),
        'y': getattr(action_output, 'y', None),
      }
      step_actions.append(action_dict)
    else:
      step_actions.append({'step': step_n + 1, 'action_type': None})

    # 保存所有 action 到 JSON 文件
    if save_img_path and step_actions:
      actions_json_path = os.path.join(save_img_path, 'actions.json')
      with open(actions_json_path, 'w', encoding='utf-8') as f:
        json.dump({'steps': step_actions}, f, ensure_ascii=False, indent=2)
    if termination_fn(agent.env):
      print_fn('Environment ends episode.')
      return EpisodeResult(
          done=True,
          step_data=_transpose_lod_to_dol(output),
          user_history=user_history,
      )
    elif result.done:
      print_fn('Agent indicates task is done.')
      return EpisodeResult(
          done=result.done,
          step_data=_transpose_lod_to_dol(output),
          user_history=user_history,
      )
  print_fn(
      termcolor.colored(
          'Agent did not indicate task is done. Reached max number of steps.',
          'red',
      )
  )
  return EpisodeResult(
      done=result.done, step_data=_transpose_lod_to_dol(output), user_history=user_history  # pylint: disable=undefined-variable
  )

def _transpose_lod_to_dol(data: list[dict[str, Any]]) -> dict[str, list[Any]]:
  """Transposes a list of dictionaries to a dictionary of lists.

  Args:
    data: A list of dictionaries.

  Returns:
    A dictionary where each key is from the input dictionaries and each value is
    a list of values for that key.
  """
  result = {}
  for d in data:
    for key, value in d.items():
      if key not in result:
        result[key] = []
      result[key].append(value)
  return result


def transpose_dol_to_lod(data: dict[str, list[Any]]) -> list[dict[str, Any]]:
  """Converts a dictionary of lists to a list of dictionaries.

  Useful for post-processing of results; e.g., in colab.

  Args:
    data: A dictionary where each value is a list.

  Returns:
    A list of dictionaries.
  """
  return [dict(zip(data.keys(), values)) for values in zip(*data.values())]
