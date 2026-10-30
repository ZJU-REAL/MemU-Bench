

"""固定任务：短任务集合。

包含以下任务：
- CalendarAddEvent: 日历中添加一个日程
- ClockDeleteAlarm: 删除闹钟
- ContactsAddContact: 新建一个联系人
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import calendar as calendar_validator
from android_world.task_evals.custom_validators import clock as clock_validator
from android_world.task_evals.custom_validators import contacts as contacts_validator
from android_world.task_evals.custom_validators import files as files_validator


class User0Short_CalendarAddEvent(fixed_task_eval.TaskEval):
  """固定任务：验证日历事件是否被添加。

  Agent 需要在 Simple Calendar Pro 应用中添加一个日程事件。
  验证方式：比较任务执行前后的数据库状态。
  """

  complexity = 4.0
  app_name = "simple calendar"
  # 固定的事件参数
  _EVENT_TITLE = "Picnic"
  _EVENT_START_TS = 1777644000  
  _EVENT_END_TS = 1777658400 
  _EVENT_LOCATION = "Barstow"
  _SNAPSHOT_NAME = "snapshot_0_short"
  @property
  def goal(self) -> str:
    return f"I plan to have a picnic at the location I just marked on the map from 2 p.m. to 6 p.m. the day after tomorrow. Please help me add this schedule to the {self.app_name} app."
  
  @property
  def full_goal(self) -> str:
    return f"I plan to have a picnic at {self._EVENT_LOCATION} from 2 p.m. to 6 p.m. the day after tomorrow. Please help me add this schedule to the {self.app_name} app."
  
  @property
  def information(self):
    return 'I marked a location on the OsmAnd app.'
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
        expected_location=self._EVENT_LOCATION,
    )
    return 1.0 if result else 0.0


class User0Short_ClockDeleteAlarm(fixed_task_eval.TaskEval):
  """固定任务：验证闹钟是否被删除。

  Agent 需要在 Clock 应用中删除指定的闹钟。
  验证方式：通过 UI 检查闹钟是否不再存在。
  """

  complexity = 4.0
  app_name = "clock"
  # 固定的闹钟参数
  _ALARM_HOUR = 14
  _ALARM_MINUTE = 0
  _SNAPSHOT_NAME = "snapshot_0_short"
  @property
  def goal(self) -> str:
    return f"Please delete the alarm I just set."
  
  @property
  def full_goal(self) -> str:
    return f"Please delete the alarm for 14:00"
  
  @property
  def information(self):
    return 'I just set an afternoon alarm.'
  
  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print("[DEBUG] Initializing clock delete alarm task...")
    # 注意：闹钟删除验证通过 UI 检查，不需要存储前置状态

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = clock_validator.validate_alarm_deleted(
        env=env,
        alarm_hour=self._ALARM_HOUR,
        alarm_minute=self._ALARM_MINUTE,
        required_texts=["8", "30", "9", "10", "00"]
    )
    return 1.0 if result else 0.0


class User0Short_ContactsAddContact(fixed_task_eval.TaskEval):
  """固定任务：验证联系人是否被添加。

  Agent 需要在 Contacts 应用中创建一个新联系人。
  验证方式：比较任务执行前后的联系人列表。
  """

  complexity = 4.0
  app_name = "contacts"
  # 固定的联系人参数
  _CONTACT_NAME = "Courier"
  _CONTACT_NUMBER = "13811223344"
  _SNAPSHOT_NAME = "snapshot_0_short"
  @property
  def goal(self) -> str:
    return f"Save the first call this morning as a contact named Courier in {self.app_name} app."
  @property
  def full_goal(self) -> str:
    return f"Save the number {self._CONTACT_NUMBER} as a contact named Courier in {self.app_name} app."
  
  @property
  def information(self):
    return "That person's phone number starts with 138."
  
  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print("[DEBUG] Initializing contacts add task...")
    self._before_contacts = contacts_validator.get_contacts(env)
    print(f"[DEBUG] Stored before state: {len(self._before_contacts)} contacts")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_contacts'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = contacts_validator.validate_contact_added(
        env=env,
        before_contacts=self._before_contacts,
        expected_name=self._CONTACT_NAME,
        expected_number=self._CONTACT_NUMBER,
    )
    return 1.0 if result else 0.0

