

"""固定任务：短任务集合。

包含以下任务：
- PhoneCallDebtor: 根据账单信息打电话给欠款人
- ExpenseAddSalary: 根据短信记录工资收入
- RetroMusicPlaySong: 在 Retro Music 中播放指定歌曲
- SmsSendExpenseToContact: 给联系人发送消费金额短信
"""

import time

from android_world.env import adb_utils
from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import expense as expense_validator
from android_world.task_evals.custom_validators import phone as phone_validator
from android_world.task_evals.custom_validators import retro_music as retro_music_validator
from android_world.task_evals.custom_validators import sms as sms_validator


class User5Short_PhoneCallDebtor(fixed_task_eval.TaskEval):
  """固定任务：根据账单信息打电话给欠款人。

  Agent 需要查看账单后，打电话给欠钱的人。
  验证方式：检查拨号界面是否显示了正确的号码。
  """

  app_name = "phone"

  complexity = 4.0

  # 固定的电话参数
  _PHONE_NUMBER = "5552283138"
  _CONTACT_NAME = "David Johnson"
  _SNAPSHOT_NAME = "snapshot_5_short"

  @property
  def goal(self) -> str:
    return f"Please call the person who owes me money in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Call David Johnson in {self.app_name} app."

  @property
  def information(self) -> str:
    return "I viewed a bill of lending money to someone on the Pro Expense app."
  
  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    # 清理残留的电话状态，避免快照恢复后残留通话导致 conference call
    # 注意：只结束进行中的通话，不清除通话记录
    adb_utils.end_call_if_active(env.controller)
    time.sleep(1)
    print(f"[DEBUG] Initializing phone call debtor task...")
    print(f"[DEBUG] Target number: {self._PHONE_NUMBER}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = phone_validator.called_correct_number(
        env=env,
        phone_number=self._PHONE_NUMBER,
        contact_name=self._CONTACT_NAME,
    )
    return 1.0 if result else 0.0


class User5Short_ExpenseAddSalary(fixed_task_eval.TaskEval):
  """固定任务：根据短信中的工资消息记录收入。

  Agent 需要根据短信中的工资信息，在记账软件中记录一笔收入。
  验证方式：比较任务执行前后的记账数据库，检查新增记录是否匹配。
  """

  app_name = "pro expense"

  complexity = 4.0

  # 固定的记账参数
  _EXPENSE_NAME = "Salary"
  _EXPENSE_AMOUNT = 800000  # 8000元，单位：分
  _SNAPSHOT_NAME = "snapshot_5_short"
  _CATEGORY = "Income"
  @property
  def goal(self) -> str:
    return f"Please record my salary in the {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Record an income of 8000 yuan as salary in the {self.app_name} app."

  @property
  def information(self) -> str:
    return "I just received a text message from a number starting with 138 in the simple sms messenger app, saying that my salary has been credited."
  
  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_expenses = expense_validator.get_expenses(env)
    print(f"[DEBUG] Initializing expense add salary task...")
    print(f"[DEBUG] Before expenses: {len(self._before_expenses)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_expenses'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = expense_validator.validate_expense_added(
        env=env,
        goal=self.full_goal,
        before_expenses=self._before_expenses,
        expected_name=self._EXPENSE_NAME,
        expected_amount=self._EXPENSE_AMOUNT,
        expected_category=self._CATEGORY
    )
    return 1.0 if result else 0.0


class User5Short_RetroMusicPlaySong(fixed_task_eval.TaskEval):
  """固定任务：验证歌曲是否正在播放。

  Agent 需要在 Retro Music 应用中播放指定的歌曲。
  验证方式：检查音乐播放状态数据库。
  """

  app_name = "retro music"

  complexity = 4.0

  # 固定的音乐参数
  _SONG_TITLE = "Moments"
  _SNAPSHOT_NAME = "snapshot_5_short"

  @property
  def goal(self) -> str:
    return f"Please play the song my friend recommended for me in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Please play the song '{self._SONG_TITLE}' for me in {self.app_name} app."

  @property
  def information(self) -> str:
    return "Mary Brown sent me a message recommending a song on the Simple SMS Messenger app."
  
  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print("[DEBUG] Initializing retro music play song task...")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = retro_music_validator.validate_song_playing(
        env=env,
        expected_song_title=self._SONG_TITLE,
    )
    return 1.0 if result else 0.0


class User5Short_SmsSendExpenseToContact(fixed_task_eval.TaskEval):
  """固定任务：验证短信是否已发送给联系人。

  Agent 需要在短信应用中向联系人发送一条关于花费的短信。
  验证方式：检查短信数据库中是否已发送该短信。
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  # 固定的短信参数
  _CONTACT_NAME = "Mary Brown"
  _PHONE_NUMBER = "5556136850"
  _MESSAGE_BODY = "I spent 9000 yuan."
  _SNAPSHOT_NAME = "snapshot_5_short"

  @property
  def goal(self) -> str:
    return f"I calculated my total expenses. Please tell Mary Brown how much I spent via {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Send a text message to Mary Brown via {self.app_name} app, saying: I spent 9000 yuan."

  @property
  def information(self) -> str:
    return "I just calculated the amount with the calculator."
  
  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print("[DEBUG] Initializing sms send expense task...")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = sms_validator.validate_sms_sent(
        env=env,
        goal=self.full_goal,
        phone_number=self._PHONE_NUMBER,
        expected_body=self._MESSAGE_BODY,
    )
    return 1.0 if result else 0.0