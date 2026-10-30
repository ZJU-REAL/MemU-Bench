

"""Run eval suite.

The run.py module is used to run a suite of tasks, with configurable task
combinations, environment setups, and agent configurations. You can run specific
tasks or all tasks in the suite and customize various settings using the
command-line flags.
"""

from collections.abc import Sequence
import importlib
import os
from dotenv import load_dotenv

from absl import app
from absl import flags
from absl import logging

# Suppress gRPC logs before any imports
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GRPC_TRACE'] = 'none'
os.environ['GRPC_ENABLE_FORK_SUPPORT'] = 'false'  # Disable fork support to avoid fork_posix logs
from android_world import checkpointer as checkpointer_lib
from android_world import registry
from android_world import suite_utils
from android_world.agents import base_agent
from android_world.agents import human_agent
from android_world.agents import human_count_step_agent
from android_world.agents import infer
from android_world.env import env_launcher
from android_world.env import interface

logging.set_verbosity(logging.WARNING)

# API credentials are now loaded from .env file
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

_DEVICE_CONSOLE_PORT = flags.DEFINE_integer(
    'console_port',
    5554,
    'The console port of the running Android device. This can usually be'
    ' retrieved by looking at the output of `adb devices`. In general, the'
    ' first connected device is port 5554, the second is 5556, and'
    ' so on.',
)

_SUITE_FAMILY = flags.DEFINE_enum(
    'suite_family',
    registry.TaskRegistry.ANDROID_WORLD_FAMILY,
    [
        # Families from the paper.
        registry.TaskRegistry.ANDROID_WORLD_FAMILY,
        registry.TaskRegistry.MINIWOB_FAMILY_SUBSET,
        # Other families for more testing.
        registry.TaskRegistry.MINIWOB_FAMILY,
        registry.TaskRegistry.ANDROID_FAMILY,
        registry.TaskRegistry.INFORMATION_RETRIEVAL_FAMILY,
        # Debug suite for testing.
        registry.TaskRegistry.DEBUG_SUITE,
        registry.TaskRegistry.MEMORY_FAMILY,
    ],
    'Suite family to run. See registry.py for more information.',
)


_TASKS = flags.DEFINE_list(
    'tasks',
    None,
    'List of specific tasks to run in the given suite family. If None, run all'
    ' tasks in the suite family.',
)


_CHECKPOINT_DIR = flags.DEFINE_string(
    'checkpoint_dir',
    '',
    'The directory to save checkpoints and resume evaluation from. If the'
    ' directory contains existing checkpoint files, evaluation will resume from'
    ' the latest checkpoint. If the directory is empty or does not exist, a new'
    ' directory will be created.',
)
_OUTPUT_PATH = flags.DEFINE_string(
    'output_path',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'runs'),
    'The path to save results to if not resuming from a checkpoint is not'
    ' provided.',
)

# Agent specific.
# 优先从环境变量 MODEL 获取模型名称
_AGENT_NAME = flags.DEFINE_string(
    'agent_name',
    None,
    'Agent name. Can also be set via MODEL environment variable.',
)
_METHOD = flags.DEFINE_string(
    'method',
    'without_history',
    'Method to use. Supported: with_history, without_history, human, human_count_step.',
)
_EVAL_SETTING = flags.DEFINE_string(
    'eval_setting',
    'full_goal',
    'Evaluation setting. Supported: full_goal, unclear_goal.',
)
_USER_INFORMATION_PATH = flags.DEFINE_string(
    'user_information_path',
    None,
    'Path to the pre-generated user_history JSON file (output of generate_user_history.py). '
    'If provided, user_history for each goal will be looked up from this file.',
)
_ASK = flags.DEFINE_bool(
    'ask',
    False,
    'Whether to enable ask mode in agent.step().',
)

_ENV_FILE = flags.DEFINE_string(
    'env_file',
    '.env',
    'Path to the environment variables file. Defaults to .env',
)

_GENERATION_CONFIG = {
  'Qwen3.5-397B-A17B': {'temperature': 0},
  'Claude-Opus-4.8': {'temperature': 0},
  'gemini-3.1-pro-preview': {'temperature': 0},
  'google/gemini-3.1-pro-preview': {'temperature': 0},
}

def _get_agent(
    env: interface.AsyncEnv,
    agent_name: str,
    family: str | None = None,
) -> base_agent.EnvironmentInteractingAgent:
  """Gets agent."""
  print('Initializing agent...')
  agent = None
  if _METHOD.value == 'human':
    agent = human_agent.HumanAgent(env)
  elif _METHOD.value == 'human_count_step':
    agent = human_count_step_agent.HumanCountStepAgent(env)
  else:
    llm = infer.GeneralWrapper(agent_name, generation_config=_GENERATION_CONFIG.get(agent_name, {}))
    if agent_name in ["Qwen3.5-397B-A17B", "claude-opus-4-8", "openai/gpt-5.5", "google/gemini-3.1-pro-preview", "dashscope/qwen3.8-max", "dashscope/qwen3.5-397b-a17b"]:
      from android_world.agents import seeact_v
      agent = seeact_v.SeeAct_V(env, llm)
    elif agent_name in ["Qwen3-VL-8B-Instruct", "Qwen3-VL-32B-Instruct"]:
      from android_world.agents import qwen3vl
      agent = qwen3vl.Qwen3VLAgent(env, llm)
    elif "MAI-UI-8B" in agent_name:
      from android_world.agents import mai_ui
      agent = mai_ui.MAI_UIAgent(env, llm)
    elif "UI-Venus" in agent_name:
      from android_world.agents import ui_venus_1_5
      agent = ui_venus_1_5.UI_Venus_1_5(env, llm)
    elif "GUI-Owl" in agent_name:
      from android_world.agents import gui_owl_1_5
      agent = gui_owl_1_5.GUIOwl15Agent(env, llm)
    else:
        raise ValueError(f'Unknown method: {_METHOD.value}')

  if not agent:
    raise ValueError(f'Unknown agent: {agent_name}')

  agent.name = agent_name

  return agent


def _main() -> None:
  """Runs eval suite and gets rewards back."""
  # Load fixed environment variables from fixed.env first
  project_root = os.path.dirname(os.path.abspath(__file__))
  fixed_env_path = os.path.join(project_root, 'fixed.env')
  if os.path.isfile(fixed_env_path):
    load_dotenv(fixed_env_path, override=True)
    logging.info(f'Loaded fixed environment variables from {fixed_env_path}')
  else:
    logging.warning(f'Fixed env file not found: {fixed_env_path}')

  # Load environment variables from specified .env file (optional, can override fixed.env)
  env_file_path = _ENV_FILE.value
  if os.path.isfile(env_file_path):
    load_dotenv(env_file_path, override=True)
    logging.info(f'Loaded environment variables from {env_file_path}')
  else:
    logging.warning(f'Env file not found: {env_file_path}, using system environment variables')

  # 检查 method 和 user_information_path 的捆绑关系
  if _METHOD.value == 'with_history' and _USER_INFORMATION_PATH.value is None:
    raise ValueError(
        'When using --method=with_history, you must also provide '
        '--user_information_path=<path_to_user_history_json>\n'
        'Example: python run_memubench.py --method with_history '
        '--user_information_path /path/to/user_history_result.json'
    )

  # 检查是否指定了模型（环境变量或命令行参数）
  # 如果命令行没有指定，尝试从环境变量获取
  agent_name = _AGENT_NAME.value
  if _METHOD.value != 'human_count_step' and agent_name is None:
    agent_name = os.environ.get('MODEL', None)
    if agent_name is None:
      raise ValueError(
          'Agent name must be specified! Either:\n'
          '  1. Set environment variable: export MODEL=your_model_name\n'
          '  2. Or use command line flag: --agent_name=your_model_name\n'
          'Example: export MODEL=anthropic/claude-sonnet-4.6'
      )

  # 检查 eval_setting 的值
  _VALID_EVAL_SETTINGS = ['full_goal', 'unclear_goal']
  if _EVAL_SETTING.value not in _VALID_EVAL_SETTINGS:
    raise ValueError(
        f'Invalid eval_setting: {_EVAL_SETTING.value}.\n'
        f'Valid values are: {_VALID_EVAL_SETTINGS}'
    )

  env = env_launcher.load_and_setup_env(
      console_port=_DEVICE_CONSOLE_PORT.value,
      # emulator_setup=_EMULATOR_SETUP.value,
      adb_path=_ADB_PATH.value,
  )

  task_registry = registry.TaskRegistry()
  suite = suite_utils.create_suite(
      task_registry.get_registry(family=_SUITE_FAMILY.value),
      tasks=_TASKS.value,
  )
  suite.suite_family = _SUITE_FAMILY.value

  agent = _get_agent(env, agent_name, _SUITE_FAMILY.value)

  # 设置评估方式：full_goal 使用 full_goal，其他 (unclear_goal) 使用 goal
  suite.use_full_goal = (_EVAL_SETTING.value == 'full_goal')
  agent.transition_pause = None

  if _CHECKPOINT_DIR.value:
    checkpoint_dir = _CHECKPOINT_DIR.value
  else:
    checkpoint_dir = checkpointer_lib.create_run_directory(_OUTPUT_PATH.value)

  # path points to the pre-generated user_history JSON file
  path = _USER_INFORMATION_PATH.value

  print(
      f'Starting eval with agent {agent_name} and writing to'
      f' {checkpoint_dir}'
  )
  suite_utils.run(
      suite,
      agent,
      checkpointer=checkpointer_lib.IncrementalCheckpointer(checkpoint_dir),
      demo_mode=False,
      path=path,
      ask=_ASK.value,
  )
  print(
      f'Finished running agent {agent_name} on {_SUITE_FAMILY.value}'
      f' family. Wrote to {checkpoint_dir}.'
  )
  env.close()


def main(argv: Sequence[str]) -> None:
  del argv
  _main()


if __name__ == '__main__':
  app.run(main)