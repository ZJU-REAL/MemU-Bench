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

"""Debug evaluators for Clock (Alarm) app tasks.

These evaluators verify alarm operations (add/delete/enable/disable) by checking
the Android alarm content provider.
"""

from android_world.env import adb_utils
from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import clock as clock_validator


class DebugAlarmAdd(fixed_task_eval.TaskEval):
  """固定任务：验证闹钟是否被添加。

  Agent 需要在 Clock 应用中添加一个闹钟。
  验证方式：检查 Android alarm content provider。
  """

  complexity = 1.0

  # 固定的闹钟参数
  _ALARM_HOUR = 7
  _ALARM_MINUTE = 30
  _ALARM_LABEL = "Morning alarm"

  @property
  def goal(self) -> str:
    """任务目标。"""
    return (f"In the Clock app, create a new alarm at {self._ALARM_HOUR:02d}:{self._ALARM_MINUTE:02d} "
            f"with the label '{self._ALARM_LABEL}'")

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空所有闹钟。"""
    print("[DEBUG] Clearing all alarms...")
    clock_validator.clear_alarms(env)
    print("[DEBUG] Alarms cleared")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    result = clock_validator.validate_alarm_added(
        env=env,
        expected_hour=self._ALARM_HOUR,
        expected_minute=self._ALARM_MINUTE,
        expected_label=self._ALARM_LABEL,
    )
    return 1.0 if result else 0.0


class DebugAlarmDelete(fixed_task_eval.TaskEval):
  """固定任务：验证闹钟是否被删除。

  Agent 需要在 Clock 应用中删除指定的闹钟。
  验证方式：检查 Android alarm content provider。
  """

  complexity = 1.0

  # 固定的闹钟参数
  _ALARM_HOUR = 8
  _ALARM_MINUTE = 30

  @property
  def goal(self) -> str:
    """任务目标。"""
    return f"In the Clock app, delete the alarm at {self._ALARM_HOUR:02d}:{self._ALARM_MINUTE:02d}"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空闹钟，添加预设闹钟。"""
    print("[DEBUG] Clearing all alarms...")
    clock_validator.clear_alarms(env)
    print("[DEBUG] Alarms cleared")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    result = clock_validator.validate_alarm_deleted(
        env=env,
        alarm_hour=self._ALARM_HOUR,
        alarm_minute=self._ALARM_MINUTE,
    )
    return 1.0 if result else 0.0


