

"""固定任务：中等任务集合。

包含以下任务：
- GalleryDeleteScreenshot: 删除相册中的截图
- ContactsAddContact: 添加联系人
- ClockSetAlarm: 设置闹钟
- CalendarAddEvent: 添加日历事件
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import calendar as calendar_validator
from android_world.task_evals.custom_validators import clock as clock_validator
from android_world.task_evals.custom_validators import contacts as contacts_validator
from android_world.task_evals.custom_validators import files as files_validator


class User3Medium_GalleryDeleteScreenshot(fixed_task_eval.TaskEval):
  """固定任务：删除相册中的截图。

  Agent 需要在 Simple Gallery Pro 中删除玩游戏时不小心保存的截图。
  验证方式：检查文件系统中该截图是否已被删除，且其他文件未被误删。
  """

  app_name = "simple gallery"

  complexity = 4.0

  _FILE_NAME = "screenshot.png"
  _FILE_DIRECTORY = "/sdcard/DCIM"
  _SNAPSHOT_NAME = "snapshot_3_medium"

  def __init__(self):
    super().__init__()
    self._initial_files = None

  @property
  def goal(self) -> str:
    return f"Delete the screenshot I accidentally saved while playing a game earlier from {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Delete the file named {self._FILE_NAME} from {self.app_name} app."

  @property
  def information(self):
    return "I accidentally took a screenshot while playing the game 2048."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._initial_files = [
        f.name for f in files_validator.get_files_in_directory(
            env, self._FILE_DIRECTORY
        )
    ]
    print(f"[DEBUG] Initializing gallery delete screenshot task...")
    print(f"[DEBUG] Target file: {self._FILE_NAME} in {self._FILE_DIRECTORY}")
    print(f"[DEBUG] Initial files in directory: {self._initial_files}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if self._initial_files is None:
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = files_validator.validate_file_deleted(
        env=env,
        file_name=self._FILE_NAME,
        directory_path=self._FILE_DIRECTORY,
        initial_files=self._initial_files,
    )
    return 1.0 if result else 0.0


class User3Medium_ContactsAddContact(fixed_task_eval.TaskEval):
  """固定任务：添加联系人。

  Agent 需要在 Contacts 应用中将本机号码存为联系人。
  验证方式：比较任务执行前后的联系人列表，检查新增联系人是否匹配。
  """

  app_name = "contacts"

  complexity = 4.0

  _CONTACT_NAME = "my phone"
  _CONTACT_NUMBER = "15551234567"
  _SNAPSHOT_NAME = "snapshot_3_medium"

  @property
  def goal(self) -> str:
    return f"Save my phone number as a contact in {self.app_name} app. First name is 'my phone'."

  @property
  def full_goal(self) -> str:
    return f"Save the phone number {self._CONTACT_NUMBER} as a contact with the first name '{self._CONTACT_NAME}' in {self.app_name} app."

  @property
  def information(self):
    return "I checked my phone number in the settings earlier."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_contacts = contacts_validator.get_contacts(env)
    print(f"[DEBUG] Initializing contacts add task...")
    print(f"[DEBUG] Before contacts: {len(self._before_contacts)}")

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


class User3Medium_ClockSetAlarm(fixed_task_eval.TaskEval):
  """固定任务：设置闹钟。

  Agent 需要在 Clock 应用中设置一个周日中午12点的闹钟。
  验证方式：通过 UI 检查闹钟是否被正确添加，同时验证屏幕上显示周日和重复设置。
  """

  app_name = "clock"

  complexity = 4.0

  _ALARM_HOUR = 12
  _ALARM_MINUTE = 0
  _FUZZY_MINUTES = 3
  _REQUIRED_TEXTS = ["Sunday"]  # 需要出现在屏幕上的额外文本
  _SNAPSHOT_NAME = "snapshot_3_medium"

  @property
  def goal(self) -> str:
    return f"I created a to-do for an event earlier, please set an alarm one hour before it for me in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Set an alarm for 12:00 AM on Sunday in {self.app_name} app."

  @property
  def information(self):
    return "I created a to-do in the tasks app for going out on Sunday."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing clock set alarm task...")
    print(f"[DEBUG] Expected alarm: {self._ALARM_HOUR:02d}:{self._ALARM_MINUTE:02d}")
    print(f"[DEBUG] Required texts: {self._REQUIRED_TEXTS}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = clock_validator.validate_alarm_added(
        env=env,
        expected_hour=self._ALARM_HOUR,
        expected_minute=self._ALARM_MINUTE,
        fuzzy_minutes=self._FUZZY_MINUTES,
        required_texts=self._REQUIRED_TEXTS,
    )
    return 1.0 if result else 0.0


class User3Medium_CalendarAddEvent(fixed_task_eval.TaskEval):
  """固定任务：添加日历事件。

  Agent 需要在 Simple Calendar Pro 中添加一个日程事件。
  验证方式：比较任务执行前后的数据库状态，检查新增事件是否匹配。
  """

  app_name = "simple calendar"

  complexity = 4.0

  _EVENT_TITLE = "outing"
  _EVENT_LOCATION = "West Menlo Park"
  _EVENT_START_TS = 1777766400   # 2026-05-03 00:00:00 UTC
  _EVENT_END_TS = 1777809600     # 2026-05-03 12:00:00 UTC
  _SNAPSHOT_NAME = "snapshot_3_medium"

  @property
  def goal(self) -> str:
    return f"Modify the outing event location in {self.app_name} app. If it doesn't exist, please create it as an all-day event."

  @property
  def full_goal(self) -> str:
    return f"Add an all-day outing event on Sunday at {self._EVENT_LOCATION} in {self.app_name} app."

  @property
  def information(self):
    return "Jessica Garcia texted me that the Sunday event location has changed via simple sms messenger app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_events = calendar_validator.get_current_events(env)
    print(f"[DEBUG] Initializing calendar add event task...")
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