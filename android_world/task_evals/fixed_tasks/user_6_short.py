

"""固定任务：短任务集合。

包含以下任务：
- ExpenseRecordDinner: 记录聚餐消费
- TasksCreateMeeting: 创建会议待办
- CalendarAddTrip: 创建去纽约的日程
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import calendar as calendar_validator
from android_world.task_evals.custom_validators import expense as expense_validator
from android_world.task_evals.custom_validators import task as task_validator


class User6Short_ExpenseRecordDinner(fixed_task_eval.TaskEval):
  """固定任务：在 Pro Expense 中记录聚餐消费。

  Agent 需要在 Pro Expense 应用中记录一笔消费，
  名字是聚餐，金额是 50 元，类别是 social。
  验证方式：使用 LLM 判断记账记录是否符合要求。
  """

  app_name = "pro expense"

  complexity = 4.0

  _EXPENSE_NAME = "dinner"
  _EXPENSE_AMOUNT = 5000  # 50元，单位：分
  _CATEGORY = "Social"
  _SNAPSHOT_NAME = "snapshot_6_short"

  @property
  def goal(self) -> str:
    return f"Record yesterday's dinner expense in {self.app_name} app, name it 'dinner', category is 'social'."

  @property
  def full_goal(self) -> str:
    return f"Record an expense in {self.app_name} app named '{self._EXPENSE_NAME}' with amount 50 yuan and category '{self._CATEGORY}'."

  @property
  def information(self):
    return "Thomas Anderson texted me via simple sms messenger app telling me how much I need to transfer to him."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_expenses = expense_validator.get_expenses(env)
    print(f"[DEBUG] Initializing expense record dinner task...")
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
        expected_category=self._CATEGORY,
    )
    return 1.0 if result else 0.0


class User6Short_TasksCreateMeeting(fixed_task_eval.TaskEval):
  """固定任务：在 Tasks 中创建会议待办。

  Agent 需要在 Tasks 应用中创建一个会议待办，
  名字是和Sarah Jones的会议，时间是5月19日。
  验证方式：使用 LLM 判断待办内容是否符合要求。
  """

  app_name = "tasks"

  complexity = 4.0

  _TASK_TITLE = "Meeting with Sarah Jones"
  _DUE_DATE = "2026-05-19"
  _DUE_DATE_TS = 1779192000000  # 2026-05-19
  _SNAPSHOT_NAME = "snapshot_6_short"

  @property
  def goal(self) -> str:
    return f"Create a todo for the meeting with Sarah Jones in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Create a todo in {self.app_name} app named '{self._TASK_TITLE}' with due date {self._DUE_DATE}."

  @property
  def information(self):
    return "I have two meeting schedules recorded in one day in simple calendar app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_tasks = task_validator.get_tasks(env)
    print(f"[DEBUG] Initializing tasks create meeting task...")
    print(f"[DEBUG] Before tasks: {len(self._before_tasks)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_tasks'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = task_validator.validate_task_added(
        env=env,
        goal=self.full_goal,
        before_tasks=self._before_tasks,
        expected_title=self._TASK_TITLE,
        expected_due_date=self._DUE_DATE_TS,
    )
    return 1.0 if result else 0.0


class User6Short_CalendarAddTrip(fixed_task_eval.TaskEval):
  """固定任务：在 Simple Calendar 中创建去纽约的日程。

  Agent 需要在 Simple Calendar 应用中创建一个去纽约的日程，
  日期是5月30日，持续时间是一整天。
  验证方式：检查日历数据库中是否有对应的事件。
  """

  app_name = "simple calendar"

  complexity = 4.0

  _EVENT_TITLE = "Trip to New York"
  # _EVENT_START_TS = 1780099200  # 2026-05-30 00:00:00 UTC
  # _EVENT_END_TS = 1780142400  # 2026-05-31 00:00:00 UTC
  _EVENT_LOCATION = "New York"
  _SNAPSHOT_NAME = "snapshot_6_short"

  @property
  def goal(self) -> str:
    return f"I browsed a city before, please create a calendar event on May 30 to go there in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Create an all-day event in {self.app_name} app titled '{self._EVENT_TITLE}' on May 30 with location '{self._EVENT_LOCATION}'."

  @property
  def information(self) -> str:
    return "I browsed that city on the chrome."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_events = calendar_validator.get_current_events(env)
    print(f"[DEBUG] Initializing calendar add trip task...")
    print(f"[DEBUG] Before events: {len(self._before_events)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_events'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = calendar_validator.validate_event_added(
        env=env,
        goal=self.full_goal,
        before_events=self._before_events,
        expected_title=self._EVENT_TITLE,
        # expected_start_ts=self._EVENT_START_TS,
        # expected_end_ts=self._EVENT_END_TS,
        expected_location=self._EVENT_LOCATION,
    )
    return 1.0 if result else 0.0