

"""固定任务：短任务集合。

包含以下任务：
- SMSSendGamesToJennifer: 给 Jennifer Smith 发短信告知最近在玩的游戏
- PhoneCallRepairman: 给维修工打电话
- JoplinCreateNoteReading: 创建阅读笔记
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import joplin as joplin_validator
from android_world.task_evals.custom_validators import phone as phone_validator
from android_world.task_evals.custom_validators import sms as sms_validator


class User10Short_SMSSendGamesToJennifer(fixed_task_eval.TaskEval):
  """固定任务：给 Jennifer Smith 发短信告知最近在玩的游戏。

  Agent 需要在 Simple SMS Messenger 中给 Jennifer Smith 发送短信，
  内容是最近在玩 2048 和 Solitairecg 这两款游戏。
  验证方式：检查短信数据库中是否有发送给目标号码的短信，且内容匹配。
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  _CONTACT_NAME = "Jennifer Smith"
  _PHONE_NUMBER = "5552200678"
  _MESSAGE_BODY = "I recently played two games: 2048 and Solitairecg"
  _SNAPSHOT_NAME = "snapshot_10_short"

  @property
  def goal(self) -> str:
    return f"Send a text message to Jennifer telling her which games I've been playing recently via {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Send a text message to {self._CONTACT_NAME} via {self.app_name} app, saying '{self._MESSAGE_BODY}'"

  @property
  def information(self):
    return "I played two games before, one is a card game, the other is a game with 16 grids where you combine numbers."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing SMS send games to Jennifer task...")
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


class User10Short_PhoneCallRepairman(fixed_task_eval.TaskEval):
  """固定任务：给维修工打电话。

  Agent 需要拨打朋友告诉的维修工电话号码 5552596770。
  验证方式：检查电话拨号界面是否显示了正确的号码。
  """

  app_name = "phone"

  complexity = 4.0

  _PHONE_NUMBER = "5552596770"
  _SNAPSHOT_NAME = "snapshot_10_short"

  @property
  def goal(self) -> str:
    return f"Call the repairman my friend told me about via {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Call {self._PHONE_NUMBER} via {self.app_name} app."

  @property
  def information(self):
    return "Charles Martinez texted me a repairman's phone number via simple sms messenger app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing phone call repairman task...")
    print(f"[DEBUG] Target number: {self._PHONE_NUMBER}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = phone_validator.called_correct_number(
        env=env,
        phone_number=self._PHONE_NUMBER,
    )
    return 1.0 if result else 0.0


class User10Short_JoplinCreateNoteReading(fixed_task_eval.TaskEval):
  """固定任务：在 Joplin 中创建阅读笔记。

  Agent 需要在 Joplin 应用中创建一个笔记，
  标题是"阅读"，内容是今天阅读了 Android World 和 Deep Residual Learning for Image Recognition 两篇论文。
  验证方式：检查笔记数据库中是否有对应的笔记。
  """

  app_name = "joplin"

  complexity = 4.0

  _NOTE_TITLE = "Reading"
  _NOTE_BODY = "Today I read the Android World paper and Deep Residual Learning for Image Recognition paper"
  _SNAPSHOT_NAME = "snapshot_10_short"

  @property
  def goal(self) -> str:
    return f"Create a note in {self.app_name} app with title 'Reading' and content about the papers I read today."

  @property
  def full_goal(self) -> str:
    return f"Create a note in {self.app_name} app with title '{self._NOTE_TITLE}' and body '{self._NOTE_BODY}'."

  @property
  def information(self):
    return "One paper name has Android in it, the other has Deep Residual in it."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_notes = joplin_validator.get_notes(env)
    print(f"[DEBUG] Initializing Joplin create note reading task...")
    print(f"[DEBUG] Before notes: {len(self._before_notes)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_notes'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    after_notes = joplin_validator.get_notes(env)
    result = joplin_validator.validate_note_created(
        before=self._before_notes,
        after=after_notes,
        title=self._NOTE_TITLE,
        body=self._NOTE_BODY,
    )
    return 1.0 if result else 0.0