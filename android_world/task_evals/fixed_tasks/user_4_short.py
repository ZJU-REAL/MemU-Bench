

"""固定任务：短任务集合。

包含以下任务：
- SMSSendBirthdayWish: 根据日历中的生日记录发送祝福短信
- SMSSendPhoneNumber: 将来电号码转发给联系人
- PhoneCallBack: 回拨未接来电
"""

import time

from android_world.env import adb_utils
from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import phone as phone_validator
from android_world.task_evals.custom_validators import sms as sms_validator


class User4Short_SMSSendBirthdayWish(fixed_task_eval.TaskEval):
  """固定任务：根据日历中的生日记录发送祝福短信。

  Agent 需要查看日历中今天的生日记录，给对应的朋友发送祝福短信。
  验证方式：检查短信数据库中是否有发送给目标号码的短信，且内容匹配。
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  # 固定的短信参数
  _CONTACT_NAME = "Mary Brown"
  _PHONE_NUMBER = "5556136850"
  _MESSAGE_BODY = "Happy Birthday"
  _SNAPSHOT_NAME = "snapshot_4_short"

  @property
  def goal(self) -> str:
    return f"Please send my friend a message via {self.app_name} app saying Happy Birthday."

  @property
  def full_goal(self) -> str:
    return (f"Send a birthday wish text message to {self._CONTACT_NAME} via {self.app_name} app,"
            f"saying: {self._MESSAGE_BODY}")
  
  @property
  def information(self) -> str:
    return "I have a friend's birthday scheduled in the Simple Calendar app."
  
  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing SMS send birthday wish task...")
    print(f"[DEBUG] Target: {self._CONTACT_NAME} ({self._PHONE_NUMBER})")
    print(f"[DEBUG] Message: {self._MESSAGE_BODY}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = sms_validator.validate_sms_sent(
        env=env,
        goal=self.full_goal,
        phone_number=self._PHONE_NUMBER,
        expected_body=self._MESSAGE_BODY,
    )
    return 1.0 if result else 0.0


class User4Short_SMSSendPhoneNumber(fixed_task_eval.TaskEval):
  """固定任务：将来电号码通过短信转发给联系人。

  Agent 需要把刚才打电话来的号码通过短信发送给 Jennifer Smith。
  验证方式：检查短信数据库中是否有发送给目标号码的短信，且内容匹配。
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  # 固定的短信参数
  _CONTACT_NAME = "Jennifer Smith"
  _PHONE_NUMBER = "5552200678"
  _MESSAGE_BODY = "18576583527"
  _SNAPSHOT_NAME = "snapshot_4_short"

  @property
  def goal(self) -> str:
    return f"Send the phone number I dialed this morning to {self._CONTACT_NAME} via {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return (f"Send the number {self._MESSAGE_BODY} "
            f"to {self._CONTACT_NAME} via {self.app_name} app.")
  
  @property
  def information(self) -> str:
    return "The phone number starts with 185."
  
  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing SMS send phone number task...")
    print(f"[DEBUG] Target: {self._CONTACT_NAME} ({self._PHONE_NUMBER})")
    print(f"[DEBUG] Message: {self._MESSAGE_BODY}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = sms_validator.validate_sms_sent(
        env=env,
        goal=self.full_goal,
        phone_number=self._PHONE_NUMBER,
        expected_body=self._MESSAGE_BODY,
    )
    return 1.0 if result else 0.0


class User4Short_PhoneCallBack(fixed_task_eval.TaskEval):
  """固定任务：回拨未接来电。

  Agent 需要回拨刚才未接的电话。
  验证方式：检查拨号界面是否显示了正确的号码。
  """

  app_name = "phone"

  complexity = 4.0

  # 固定的电话参数
  _PHONE_NUMBER = "18648653410"
  _SNAPSHOT_NAME = "snapshot_4_short"

  @property
  def goal(self) -> str:
    return f"I was busy and missed a call. Please call it back in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Call the number {self._PHONE_NUMBER} in {self.app_name} app."

  @property
  def information(self) -> str:
    return "I missed an incoming call from a number starting with 186 just now."
  
  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    # 清理残留的电话状态，避免快照恢复后残留通话导致 conference call
    # 注意：只结束进行中的通话，不清除通话记录（agent 需要查看未接来电）
    adb_utils.end_call_if_active(env.controller)
    time.sleep(1)
    print(f"[DEBUG] Initializing phone call back task...")
    print(f"[DEBUG] Target number: {self._PHONE_NUMBER}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = phone_validator.called_correct_number(
        env=env,
        phone_number=self._PHONE_NUMBER,
    )
    return 1.0 if result else 0.0