

"""固定任务：短任务集合。

包含以下任务：
- SMSSendToContact: 发送短信给指定联系人
- SMSSendVerificationCode: 发送验证码给指定联系人
- ClockSetAlarm: 根据食谱烹饪时间设置闹钟
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import clock as clock_validator
from android_world.task_evals.custom_validators import sms as sms_validator


class User1Short_SMSSendToContact(fixed_task_eval.TaskEval):
  """固定任务：验证短信是否成功发送给指定联系人。

  Agent 需要在 Simple SMS Messenger 中给指定联系人发送一条短信。
  验证方式：检查短信数据库中是否有发送给目标号码的短信，且内容匹配。
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  # 固定的短信参数
  _CONTACT_NAME = "Barbara Jones"
  _PHONE_NUMBER = "5555681480"
  _MESSAGE_BODY = '''
SPICY TUNA WRAPS

Servings: 2 servings
Time: 10 mins

Comfort food at its finest.

Ingredients:
- optional ingredients

Directions:
1. Mix canned tuna with mayo and sriracha. Spread on tortillas, add lettuce and cucumber slices, roll up. Try adding a pinch of your favorite spices for extra flavor.

Shared with https://play.google.com/store/apps/details?id=com.flauschcode.broccoli
'''.strip()
  _SNAPSHOT_NAME = "snapshot_1_short"

  @property
  def goal(self) -> str:
    return (f"Share the recipe I opened and viewed earlier with {self._CONTACT_NAME} via {self.app_name} app.")

  @property
  def full_goal(self) -> str:
    return (f"Share the Spicy Tuna Wrap recipe with {self._CONTACT_NAME} via {self.app_name} app.")

  @property
  def information(self) -> str:
    return "I previously opened and viewed the Spicy Tuna Wrap recipe on Broccoli app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing SMS send task...")
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


class User1Short_SMSSendVerificationCode(fixed_task_eval.TaskEval):
  """固定任务：将收到的验证码转发给指定联系人。

  Agent 需要将刚收到的验证码通过短信发送给指定联系人。
  验证方式：检查短信数据库中是否有发送给目标号码的短信，且内容匹配。
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  # 固定的短信参数
  _CONTACT_NAME = "Jennifer Smith"
  _PHONE_NUMBER = "5552200678"
  _MESSAGE_BODY = "8781"
  _SNAPSHOT_NAME = "snapshot_1_short"

  @property
  def goal(self) -> str:
    return (f"Send the verification code to {self._CONTACT_NAME} via {self.app_name} app.")

  @property
  def full_goal(self) -> str:
    return (f"Send the verification code I just received: {self._MESSAGE_BODY} "
            f"to {self._CONTACT_NAME} via {self.app_name} app.")
  @property
  def information(self) -> str:
    return f"I received a text message from the number 10010 in {self.app_name}, which contains a verification code."
  
  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing SMS send verification code task...")
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


class User1Short_ClockSetAlarm(fixed_task_eval.TaskEval):
  """固定任务：根据食谱烹饪时间设置闹钟。

  Agent 需要根据之前打开的食谱的烹饪时间，设置一个对应分钟后的闹钟。
  验证方式：通过 UI 检查闹钟是否被正确添加。
  """

  app_name = "clock"

  complexity = 4.0

  # 固定的闹钟参数（用户后续会修改为实际值）
  _ALARM_HOUR = 11
  _ALARM_MINUTE = 18
  _FUZZY_MINUTES = 3
  _SNAPSHOT_NAME = "snapshot_1_short"

  @property
  def goal(self) -> str:
    return ("I'm cooking according to the recipe I opened earlier, "
            f"but I forgot how long it takes. Please set an alarm for that many minutes from now in {self.app_name} app.")

  @property
  def full_goal(self) -> str:
    return f"Set an alarm for 10 minutes from now in {self.app_name} app."

  @property
  def information(self) -> str:
    return "The recipe I looked up in the Broccoli app earlier seems to be Spicy Tuna Wrap."
  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing clock set alarm task...")
    print(f"[DEBUG] Expected alarm: {self._ALARM_HOUR:02d}:{self._ALARM_MINUTE:02d}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = clock_validator.validate_alarm_added(
        env=env,
        expected_hour=self._ALARM_HOUR,
        expected_minute=self._ALARM_MINUTE,
        fuzzy_minutes=self._FUZZY_MINUTES,
    )
    return 1.0 if result else 0.0