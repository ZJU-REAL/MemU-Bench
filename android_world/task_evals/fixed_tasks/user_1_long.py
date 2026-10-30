

"""固定任务：长任务集合。

包含以下任务：
- SMSSendExpenseToContact: 给 Charles Martinez 发送短信告知消费总额
- SMSSendFavoriteSong: 给 William Brown 发送短信告知最喜欢的歌曲
- JoplinCreateNote2048: 在 Joplin 中创建笔记记录2048得分
- PhoneCallNewAttendee: 给新来的参加会议的人打电话
- SMSSendTrailWalking: 给 Mary Johnson 发送短信告知 trail walking 达标
- RetroMusicPlayFavoriteSong: 在 Retro Music 中播放最喜欢的歌曲
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import joplin as joplin_validator
from android_world.task_evals.custom_validators import phone as phone_validator
from android_world.task_evals.custom_validators import retro_music as retro_music_validator
from android_world.task_evals.custom_validators import sms as sms_validator


class User1Long_SMSSendExpenseToContact(fixed_task_eval.TaskEval):
  """固定任务：给 Charles Martinez 发送短信告知消费总额。

  Agent 需要在 Simple SMS Messenger 中给 Charles Martinez 发送短信，
  告知他在 expense-tracking app 中的消费总额。
  验证方式：检查短信数据库中是否有发送给目标号码的短信，且内容匹配。
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  _CONTACT_NAME = "Charles Martinez"
  _PHONE_NUMBER = "5552296420"
  _MESSAGE_BODY = "I spent a total of 210 in my expense-tracking app."
  _SNAPSHOT_NAME = "snapshot_1_long"

  @property
  def goal(self) -> str:
    return f"I told a friend about my expenses, please send the same text message to {self._CONTACT_NAME} via {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Send a text message to {self._CONTACT_NAME} via {self.app_name} app, saying '{self._MESSAGE_BODY}'"

  @property
  def information(self):
    return f"I texted David Johnson about my expenses via {self.app_name} app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing SMS send expense task...")
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


class User1Long_SMSSendFavoriteSong(fixed_task_eval.TaskEval):
  """固定任务：给 William Brown 发送短信告知最喜欢的歌曲。

  Agent 需要在 Simple SMS Messenger 中给 William Brown 发送短信，
  告知他最近最喜欢的歌曲是 Moments。
  验证方式：检查短信数据库中是否有发送给目标号码的短信，且内容匹配。
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  _CONTACT_NAME = "William Brown"
  _PHONE_NUMBER = "5557168331"
  _MESSAGE_BODY = "My favorite song recently is Moments."
  _SNAPSHOT_NAME = "snapshot_1_long"

  @property
  def goal(self) -> str:
    return f"Send a text message to {self._CONTACT_NAME} via {self.app_name} app about which song I like the most."

  @property
  def full_goal(self) -> str:
    return f"Send a text message to {self._CONTACT_NAME} via {self.app_name} app, saying '{self._MESSAGE_BODY}'"

  @property
  def information(self):
    return f"I don't remember the song name, but I remember I told David Johnson via {self.app_name} app what my favorite song is called."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing SMS send favorite song task...")
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


class User1Long_JoplinCreateNote2048(fixed_task_eval.TaskEval):
  """固定任务：在 Joplin 中创建笔记记录2048得分。

  Agent 需要在 Joplin 中创建一个笔记，
  标题是 2048，内容是我今天2048达到了64分。
  验证方式：比较任务执行前后的笔记数据，检查新笔记是否匹配。
  """

  app_name = "joplin"

  complexity = 4.0

  _NOTE_TITLE = "2048"
  _NOTE_BODY = "I scored 64 in 2048 today."
  _SNAPSHOT_NAME = "snapshot_1_long"

  @property
  def goal(self) -> str:
    return f"Help me create a note in {self.app_name} app with title '2048', and write about how many points I scored today."

  @property
  def full_goal(self) -> str:
    return f"Create a note in {self.app_name} app with title '{self._NOTE_TITLE}' and body '{self._NOTE_BODY}'."

  @property
  def information(self):
    return f"I texted Barbara Jones via simple sms messenger app about my 2048 score today."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_notes = joplin_validator.get_notes(env)
    print(f"[DEBUG] Initializing joplin create note 2048 task...")
    print(f"[DEBUG] Before notes: {len(self._before_notes)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_notes'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = joplin_validator.validate_note_added(
        env=env,
        goal=self.full_goal,
        before_notes=self._before_notes,
        expected_title=self._NOTE_TITLE,
        expected_body=self._NOTE_BODY,
    )
    return 1.0 if result else 0.0


class User1Long_PhoneCallNewAttendee(fixed_task_eval.TaskEval):
  """固定任务：给新来的参加会议的人打电话。

  Agent 需要给新来的参加会议的人打电话。
  验证方式：检查拨号器界面是否显示了正确的号码。
  """

  app_name = "phone"

  complexity = 4.0

  _CONTACT_NAME = "Barbara Jones"
  _PHONE_NUMBER = "5555681480"
  _SNAPSHOT_NAME = "snapshot_1_long"

  @property
  def goal(self) -> str:
    return f"Call the new meeting participant via {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Call {self._CONTACT_NAME} via {self.app_name} app."

  @property
  def information(self):
    return "Sarah Williams texted me via simple sms messenger app about who joined the meeting."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing phone call new attendee task...")
    print(f"[DEBUG] Target: {self._CONTACT_NAME} ({self._PHONE_NUMBER})")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = phone_validator.called_correct_number(
        env=env,
        phone_number=self._PHONE_NUMBER,
        contact_name=self._CONTACT_NAME,
    )
    return 1.0 if result else 0.0


class User1Long_SMSSendTrailWalking(fixed_task_eval.TaskEval):
  """固定任务：给 Mary Johnson 发送短信告知 trail walking 达标。

  Agent 需要在 Simple SMS Messenger 中给 Mary Johnson 发送短信，
  告知他 trail walking 达标了，有 7.89 英里。
  验证方式：检查短信数据库中是否有发送给目标号码的短信，且内容匹配。
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  _CONTACT_NAME = "Mary Johnson"
  _PHONE_NUMBER = "5558583792"
  _MESSAGE_BODY = "I completed my trail walking goal, 7.89 miles."
  _SNAPSHOT_NAME = "snapshot_1_long"

  @property
  def goal(self) -> str:
    return f"Send a text message to {self._CONTACT_NAME} via {self.app_name} app, saying I completed my trail walking goal and how many miles I walked"

  @property
  def full_goal(self) -> str:
    return f"Send a text message to {self._CONTACT_NAME} via {self.app_name} app, saying '{self._MESSAGE_BODY}'"

  @property
  def information(self):
    return "I viewed my exercise data on OpenTracks app earlier."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing SMS send trail walking task...")
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


class User1Long_RetroMusicPlayFavoriteSong(fixed_task_eval.TaskEval):
  """固定任务：在 Retro Music 中播放最喜欢的歌曲。

  Agent 需要在 Retro Music 中播放 Moments 这首歌。
  验证方式：检查当前播放的歌曲是否为 Moments。
  """

  app_name = "retro music"

  complexity = 4.0

  _SONG_TITLE = "Moments"
  _SNAPSHOT_NAME = "snapshot_1_long"

  @property
  def goal(self) -> str:
    return f"Play my favorite song in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Play {self._SONG_TITLE} in {self.app_name} app."

  @property
  def information(self):
    return "I don't remember the song name, but I texted David Johnson via simple sms messenger app about my favorite song."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing retro music play favorite song task...")
    print(f"[DEBUG] Expected song: {self._SONG_TITLE}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = retro_music_validator.validate_song_playing(
        env=env,
        expected_song_title=self._SONG_TITLE,
        fuzzy_match=True,
    )
    return 1.0 if result else 0.0