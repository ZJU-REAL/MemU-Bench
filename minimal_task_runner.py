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

"""Runs a single task.

The minimal_run.py module is used to run a single task, it is a minimal version
of the run.py module. A task can be specified, otherwise a random task is
selected.
"""

from collections.abc import Sequence
import os
import random
from typing import Type

from absl import app
from absl import flags
from absl import logging
from android_world import registry
from android_world.agents import infer
from android_world.agents import t3a
from android_world.env import env_launcher
from android_world.task_evals import task_eval

logging.set_verbosity(logging.WARNING)

os.environ['GRPC_VERBOSITY'] = 'ERROR'  # Only show errors
os.environ['GRPC_TRACE'] = 'none'  # Disable tracing
os.environ["API_KEY"] = 'sk-ss-v1-54234cbd9c39e99148da9ea59f43dca96bf067ef2d519474a9905a5ca9499229'

def _find_adb_directory() -> str:
  """Returns the directory where adb is located."""
  potential_paths = [
      os.path.expanduser('~/Library/Android/sdk/platform-tools/adb'),
      os.path.expanduser('~/Android/Sdk/platform-tools/adb'),
  ]
  for path in potential_paths:
    if os.path.isfile(path):
      return path
  raise EnvironmentError(
      'adb not found in the common Android SDK paths. Please install Android'
      " SDK and ensure adb is in one of the expected directories. If it's"
      ' already installed, point to the installed location.'
  )


_ADB_PATH = flags.DEFINE_string(
    'adb_path',
    _find_adb_directory(),
    'Path to adb. Set if not installed through SDK.',
)
_EMULATOR_SETUP = flags.DEFINE_boolean(
    'perform_emulator_setup',
    False,
    'Whether to perform emulator setup. This must be done once and only once'
    ' before running Android World. After an emulator is setup, this flag'
    ' should always be False.',
)
_DEVICE_CONSOLE_PORT = flags.DEFINE_integer(
    'console_port',
    5554,
    'The console port of the running Android device. This can usually be'
    ' retrieved by looking at the output of `adb devices`. In general, the'
    ' first connected device is port 5554, the second is 5556, and'
    ' so on.',
)

_TASK = flags.DEFINE_string(
    'task',
    None,
    'A specific task to run.',
)


def _main() -> None:
  """Runs a single task."""
  print('[DEBUG] Loading and setting up environment...')
  env = env_launcher.load_and_setup_env(
      console_port=_DEVICE_CONSOLE_PORT.value,
      emulator_setup=_EMULATOR_SETUP.value,
      adb_path=_ADB_PATH.value,
  )
  print('[DEBUG] Environment loaded, resetting...')
  env.reset(go_home=True)
  print('[DEBUG] Environment reset complete.')
  task_registry = registry.TaskRegistry()
  aw_registry = task_registry.get_registry(task_registry.ANDROID_WORLD_FAMILY)
  print(f'[DEBUG] Registry loaded, found {len(aw_registry)} tasks')
  if _TASK.value:
    if _TASK.value not in aw_registry:
      raise ValueError('Task {} not found in registry.'.format(_TASK.value))
    task_type: Type[task_eval.TaskEval] = aw_registry[_TASK.value]
  else:
    task_type: Type[task_eval.TaskEval] = random.choice(
        list(aw_registry.values())
    )
  print(f'[DEBUG] Task type: {task_type.__name__}')
  params = task_type.generate_random_params()
  print(f'[DEBUG] Generated params: {params}')
  task = task_type(params)
  print('[DEBUG] Initializing task...')
  task.initialize_task(env)
  print('[DEBUG] Task initialized, creating agent...')
  agent = t3a.T3A(env, infer.ClaudeWrapper('anthropic/claude-sonnet-4.6'))
  print('[DEBUG] Agent created.')

  print('Goal: ' + str(task.goal))
  is_done = False
  for _ in range(int(task.complexity * 10)):
    response = agent.step(task.goal)
    if response.done:
      is_done = True
      break
  agent_successful = is_done and task.is_successful(env) == 1
  print(
      f'{"Task Successful ✅" if agent_successful else "Task Failed ❌"};'
      f' {task.goal}'
  )
  env.close()


def main(argv: Sequence[str]) -> None:
  del argv
  _main()


if __name__ == '__main__':
  app.run(main)
