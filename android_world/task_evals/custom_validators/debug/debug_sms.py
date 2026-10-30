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

"""Debug evaluators for SMS tasks.

These evaluators verify SMS operations by checking the Android SMS database.
"""

from android_world.env import adb_utils
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.common_validators import sms_validators
from android_world.task_evals.custom_validators import sms


class DebugSmsSend(fixed_task_eval.TaskEval):
  """固定任务：验证短信是否发送成功。

  Agent 需要使用 Simple SMS Messenger 发送短信到指定号码。
  验证方式：检查 Android SMS 数据库中的已发送短信。
  """

  complexity = 1.0

  # 固定的短信参数
  _PHONE_NUMBER = "+1234567890"
  _MESSAGE_BODY = "Hello, this is a test message from the debug task."

  @property
  def goal(self) -> str:
    """任务目标。"""
    return (f"Send a text message using Simple SMS Messenger to {self._PHONE_NUMBER} "
            f"with the message: '{self._MESSAGE_BODY}'")

  def initialize_task(self, env) -> None:
    """初始化任务：清空短信数据库，确保初始状态干净。"""
    print("[DEBUG] Initializing SMS task...")
    adb_utils.toggle_airplane_mode("off", env.controller)
    sms_validators.clear_sms_and_threads(env.controller)
    print("[DEBUG] SMS database cleared")

  def is_successful(self, env) -> float:
    """判断任务是否成功。"""
    result = sms.validate_sms_sent(
        env=env,
        phone_number=self._PHONE_NUMBER,
        message_body=self._MESSAGE_BODY,
    )
    return 1.0 if result else 0.0


class DebugSmsSendMultiple(fixed_task_eval.TaskEval):
  """固定任务：验证多条短信是否发送成功。

  Agent 需要使用 Simple SMS Messenger 发送多条短信。
  验证方式：检查 Android SMS 数据库中的已发送短信。
  """

  complexity = 1.5

  # 固定的短信参数
  _MESSAGES = [
      {"number": "+1111111111", "body": "First test message"},
      {"number": "+2222222222", "body": "Second test message"},
  ]

  @property
  def goal(self) -> str:
    """任务目标。"""
    goals = []
    for msg in self._MESSAGES:
      goals.append(f"Send a text message to {msg['number']} with: '{msg['body']}'")
    return "In Simple SMS Messenger, " + " and ".join(goals)

  def initialize_task(self, env) -> None:
    """初始化任务：清空短信数据库。"""
    print("[DEBUG] Initializing multiple SMS task...")
    adb_utils.toggle_airplane_mode("off", env.controller)
    sms_validators.clear_sms_and_threads(env.controller)
    print("[DEBUG] SMS database cleared")

  def is_successful(self, env) -> float:
    """判断任务是否成功。"""
    for msg in self._MESSAGES:
      result = sms.validate_sms_sent(
          env=env,
          phone_number=msg["number"],
          message_body=msg["body"],
      )
      if not result:
        print(f"[DEBUG] Failed to validate SMS to {msg['number']}")
        return 0.0

    print("[DEBUG] All SMS validated successfully")
    return 1.0