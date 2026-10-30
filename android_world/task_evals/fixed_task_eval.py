

"""Interface for a task and the evaluation logic for that task."""

import abc
import datetime
import os
import random
from typing import Any

from absl import logging
from android_world.env import adb_utils
from android_world.env import device_constants
from android_world.env import interface
from android_world.env.setup_device import setup
from android_world.utils import app_snapshot
from android_world.utils import datetime_utils
import time

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TaskEval(abc.ABC):
  """Interface for a fixed task and its evaluation.

  Fixed tasks have a predefined goal and do not require random parameters.
  Subclasses must implement the `goal` property to define the task objective.
  """


  start_on_home_screen = True

  @property
  def save_img_path(self) -> str:
    """The path to save screenshots during agent inference.

    Each task class saves to a separate subfolder under tmp/.
    """
    task_name = self.__class__.__name__
    return os.path.join(_PROJECT_ROOT, 'tmp', task_name)

  def __init__(self):
    """Initializes the task.

    Args:
      params: Parameters dict passed by the framework. Fixed tasks typically
        ignore this, but it's required for compatibility with the task runner.
    """
    pass



  @property
  @abc.abstractmethod
  def complexity(self) -> float:
    """The complexity of the task.

    We use heuristics to dynamically allocate number of steps based on the
    complexity of the task. These are roughly calculated.

    complexity | budget
    1 | 1-10 steps
    2 | 11-20 steps
    ...
    """

  @property
  def name(self) -> str:
    """The name of the task."""
    return self.__class__.__name__

  @property
  @abc.abstractmethod
  def goal(self) -> str:
    """The task goal. Subclasses MUST implement this property."""
    pass

  @property
  @abc.abstractmethod
  def full_goal(self) -> str:
    """The task goal. Subclasses MUST implement this property."""
    pass

  @property
  @abc.abstractmethod
  def information(self) -> str:
    """The task information. Subclasses MUST implement this property."""
    pass
  
  @abc.abstractmethod
  def initialize_task(self, env: interface.AsyncEnv) -> None:  # pylint: disable=unused-argument
    """Initializes the task."""
    # 加载模拟器快照（整个系统状态，包括后台应用）
    result = adb_utils.issue_generic_request(
      ["emu", "avd", "snapshot", "load", self._SNAPSHOT_NAME],
      env.controller
    )
    output = result.generic.output.decode().strip()
    print(f"[DEBUG] Snapshot load result: {output}")

    # 检测快照加载是否失败
    if output.startswith("KO") or "doesn't exist" in output:
      raise RuntimeError(
        f"Snapshot '{self._SNAPSHOT_NAME}' does not exist on device. "
        f"Output: {output}"
      )

    # 等待模拟器恢复完成 - 使用更可靠的方式检测
    print(f"[DEBUG] Waiting for snapshot to fully load...")
    max_wait = 60  # 最多等待60秒
    for i in range(max_wait):
      time.sleep(1)
      try:
        # 尝试执行一个简单的adb命令来检测设备是否就绪
        result = adb_utils.issue_generic_request(
          ["shell", "getprop", "sys.boot_completed"],
          env.controller
        )
        boot_completed = result.generic.output.decode().strip()
        if boot_completed == "1":
          print(f"[DEBUG] Device ready after {i+1} seconds")
          break
      except Exception:
        pass
    else:
      raise RuntimeError("Timeout waiting for device to be ready after snapshot load")

    # 额外等待确保UI稳定
    time.sleep(2)
    print(f"[DEBUG] Loaded emulator snapshot: {self._SNAPSHOT_NAME}")
  
  @abc.abstractmethod
  def is_successful(self, env: interface.AsyncEnv) -> float:  # pylint: disable=unused-argument
    """Determines if the task is successful.

    Args:
      env:

    Returns:
      0: Not successful.
      1.0: Task is successful.

      For composite tasks, that combine together multiple tasks, the output is
      defined as sum(successful_tasks)/total_tasks.
    """
    pass
  
  def tear_down(self, env: interface.AsyncEnv) -> None:  # pylint: disable=unused-argument
    pass