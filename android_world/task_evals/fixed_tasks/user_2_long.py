

"""固定任务：长任务集合。

包含以下任务：
- CalendarAddInterview: 添加面试日程
- ContactsUpdateJennifer: 修改 Jennifer Smith 的电话号码
- BroccoliFavoriteRecipe: 收藏 Spicy Clams 食谱
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import calendar as calendar_validator
from android_world.task_evals.custom_validators import contacts as contacts_validator
from android_world.task_evals.custom_validators import recipe as recipe_validator


class User2Long_CalendarAddInterview(fixed_task_eval.TaskEval):
  """固定任务：添加面试日程。

  Agent 需要在 Simple Calendar Pro 中添加一个面试日程，
  日期是5月20日，时间是下午2点到3点。
  验证方式：比较任务执行前后的数据库状态，检查新增事件是否匹配。
  """

  app_name = "simple calendar"

  complexity = 4.0

  _EVENT_TITLE = "Interview"
  _EVENT_START_TS = 1779285600   # 2026-05-20 18:00:00 UTC (2pm UTC+8 = 10am UTC)
  _EVENT_END_TS = 1779289200     # 2026-05-20 19:00:00 UTC
  _SNAPSHOT_NAME = "snapshot_2_long"

  @property
  def goal(self) -> str:
    return f"Create an interview schedule in {self.app_name} app that lasts for 1 hour."

  @property
  def full_goal(self) -> str:
    return f"Add an interview event on May 20 from 14:00 to 15:00 in {self.app_name} app."

  @property
  def information(self):
    return "William Brown texted me an interview notification via simple sms messenger app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_events = calendar_validator.get_current_events(env)
    print(f"[DEBUG] Initializing calendar add interview task...")
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


class User2Long_ContactsUpdateJennifer(fixed_task_eval.TaskEval):
  """固定任务：修改 Jennifer Smith 的电话号码。

  Agent 需要在 Contacts 应用中修改 Jennifer Smith 的电话号码为 5553300678。
  验证方式：比较任务执行前后的联系人列表，检查电话号码是否已更新。
  """

  app_name = "contacts"

  complexity = 4.0

  _CONTACT_NAME = "Jennifer Smith"
  _NEW_NUMBER = "5553300678"
  _SNAPSHOT_NAME = "snapshot_2_long"

  @property
  def goal(self) -> str:
    return f"Update the phone number for {self._CONTACT_NAME} in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Update {self._CONTACT_NAME}'s phone number to {self._NEW_NUMBER} in {self.app_name} app."

  @property
  def information(self):
    return "She texted me via simple sms messenger app that she changed her phone number."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_contacts = contacts_validator.get_contacts(env)
    print(f"[DEBUG] Initializing contacts update Jennifer task...")
    print(f"[DEBUG] Before contacts: {len(self._before_contacts)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_contacts'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = contacts_validator.validate_contact_number_changed(
        env=env,
        before_contacts=self._before_contacts,
        contact_name=self._CONTACT_NAME,
        new_number=self._NEW_NUMBER,
    )
    return 1.0 if result else 0.0


class User2Long_BroccoliFavoriteRecipe(fixed_task_eval.TaskEval):
  """固定任务：收藏 Spicy Clams 食谱。

  Agent 需要在 Broccoli 食谱应用中收藏 Spicy Clams 食谱。
  验证方式：检查食谱是否已被收藏。
  """

  app_name = "broccoli"

  complexity = 4.0

  _RECIPE_TITLE = "Spicy Clams"
  _SNAPSHOT_NAME = "snapshot_2_long"

  @property
  def goal(self) -> str:
    return f"Favorite the recipe I created earlier in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Favorite the {self._RECIPE_TITLE} recipe in {self.app_name} app."

  @property
  def information(self):
    return "I created a recipe called Spicy Clams in broccoli app earlier."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing broccoli favorite recipe task...")
    print(f"[DEBUG] Target recipe: {self._RECIPE_TITLE}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = recipe_validator.validate_recipe_exists(
        env=env,
        expected={
            'title': self._RECIPE_TITLE,
            'favorite': 1,
        },
    )
    return 1.0 if result else 0.0