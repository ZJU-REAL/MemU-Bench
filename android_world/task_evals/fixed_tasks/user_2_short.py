

"""固定任务：短任务集合。

包含以下任务：
- CalendarAddEvent: 日历中添加一个日程
- ClockSetAlarm: 根据日程设置闹钟
- JoplinAddNoteFromSms: 根据短信内容创建 Joplin 笔记
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import calendar as calendar_validator
from android_world.task_evals.custom_validators import clock as clock_validator
from android_world.task_evals.custom_validators import joplin as joplin_validator


class User2Short_CalendarAddEvent(fixed_task_eval.TaskEval):
  """固定任务：验证日历事件是否被添加。

  Agent 需要在 Simple Calendar Pro 应用中添加一个日程事件。
  验证方式：比较任务执行前后的数据库状态。
  """

  complexity = 4.0
  app_name = "simple calendar"
  # 固定的事件参数
  _EVENT_TITLE = "Team Meeting"
  _EVENT_START_TS = 1778065200  # 2026-05-06 11:00:00 UTC
  _EVENT_END_TS = 1778065200  # 2026-05-06 11:00:00 UTC
  _SNAPSHOT_NAME = "snapshot_2_short"

  @property
  def goal(self) -> str:
    return f"Please add the team meeting to the {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Please add a Team Meeting event on May 6th at 11:00 AM on {self.app_name} app."
  
  @property
  def information(self) -> str:
    return "I received a text message from Mary Jones on Simple SMS Messenger app, saying the team meeting has been rescheduled."
  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)

    print("[DEBUG] Initializing calendar add event task...")
    self._before_events = calendar_validator.get_current_events(env)
    print(f"[DEBUG] Stored before state: {len(self._before_events)} events")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_events'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = calendar_validator.validate_event_added(
        env=env,
        goal=self.full_goal,
        before_events=self._before_events,
        expected_title=self._EVENT_TITLE,
        expected_start_ts=self._EVENT_START_TS,
        expected_end_ts=self._EVENT_END_TS,
    )
    return 1.0 if result else 0.0


class User2Short_ClockSetAlarm(fixed_task_eval.TaskEval):
  """固定任务：验证闹钟是否被设置。

  Agent 需要在 Clock 应用中设置一个闹钟。
  验证方式：通过 UI 检查闹钟是否存在。
  """

  complexity = 4.0
  app_name = "clock"
  # 固定的闹钟参数
  _ALARM_HOUR = 17
  _ALARM_MINUTE = 30
  _SNAPSHOT_NAME = "snapshot_2_short"

  @property
  def goal(self) -> str:
    return f"Set an alarm 2 hours earlier than the flight schedule in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Set an alarm for April 30th at 5:30 PM in {self.app_name} app."

  @property
  def information(self) -> str:
    return "I previously set a schedule for catching a flight on April 30th in the Simple Calendar app."
  
  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print("[DEBUG] Initializing clock set alarm task...")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = clock_validator.validate_alarm_added(
        env=env,
        expected_hour=self._ALARM_HOUR,
        expected_minute=self._ALARM_MINUTE,
    )
    return 1.0 if result else 0.0


class User2Short_JoplinAddNoteFromSms(fixed_task_eval.TaskEval):
  """固定任务：验证笔记是否从短信记录添加。

  Agent 需要在 Joplin 笔记应用中记录一条短信内容。
  验证方式：比较任务执行前后的笔记数据库状态。
  """

  complexity = 4.0
  app_name = "joplin"
  # 固定的笔记参数
  _NOTE_TITLE = "Going Out"
  _NOTE_BODY = "We went to Fengke Wanda for a gathering at 7 p.m. on April 30"
  _SNAPSHOT_NAME = "snapshot_2_short"

  @property
  def goal(self) -> str:
    return f"The friend texted me asking to go out and play, please record it into the {self.app_name} app with title 'Going Out' and the SMS content."

  @property
  def full_goal(self) -> str:
    return f"Friend sent me a text saying: {self._NOTE_BODY}, please help me record it in the {self.app_name} app with title 'Going Out'."

  @property
  def information(self) -> str:
    return "Mary Johnson sent me a message on Simple SMS Messenger app inviting me to hang out."
  
  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)

    print("[DEBUG] Initializing joplin add note task...")
    self._before_notes = joplin_validator.get_notes(env)
    print(f"[DEBUG] Stored before state: {len(self._before_notes)} notes")

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