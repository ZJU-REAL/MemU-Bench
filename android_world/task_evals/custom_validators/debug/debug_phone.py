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

"""Debug evaluators for Phone tasks.

These evaluators verify phone call operations.
"""

import re

from android_world.env import adb_utils
from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import phone


class DebugPhoneMakeCall(fixed_task_eval.TaskEval):
  """固定任务：验证是否拨打了指定号码。

  Agent 需要使用拨号应用拨打指定的电话号码。
  验证方式：检查通话状态和拨号界面显示的号码。
  """

  complexity = 1.0

  # 固定的电话号码
  _PHONE_NUMBER = "123456"

  @property
  def goal(self) -> str:
    """任务目标。"""
    return f"Make a phone call to the number {self._PHONE_NUMBER} and ensure the In-Call UI is displayed with options like 'Hold'."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清除通话记录和状态。"""
    print("[DEBUG] Clearing phone state...")
    phone.clear_phone_state(env.controller)
    print("[DEBUG] Phone state cleared")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。

    检查是否正在通话中，以及拨打的号码是否正确。

    Returns:
      0.0: 任务失败
      1.0: 任务成功
    """
    # 检查通话状态
    call_state = adb_utils.get_call_state(env.controller)
    print(f"[DEBUG] Call state: {call_state}")

    if call_state != "OFFHOOK":
      print("[DEBUG] Not in call. Call state is not OFFHOOK")
      return 0.0

    # 检查是否拨打了正确的号码
    if not phone.called_correct_number(env, self._PHONE_NUMBER):
      print("[DEBUG] Dialed a number, but not the correct number")
      return 0.0

    print("[DEBUG] Call validation passed")
    return 1.0

  