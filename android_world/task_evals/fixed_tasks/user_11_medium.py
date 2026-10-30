"""固定任务：中等任务集合。

包含以下任务：
- User11Medium_ExpenseRecordShopping: 在 Pro Expense 中记录网购消费
- User11Medium_ExpenseRecordTransfer: 在 Pro Expense 中记录转账收入
- User11Medium_CalendarModifyGroupMeeting: 修改 Group meeting 日程时间
- User11Medium_TasksCreateCallPhone: 创建待办提醒晚上打电话
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import calendar as calendar_validator
from android_world.task_evals.custom_validators import expense as expense_validator
from android_world.task_evals.custom_validators import task as task_validator


class User11Medium_ExpenseRecordShopping(fixed_task_eval.TaskEval):
  """固定任务：在 Pro Expense 中记录网购消费。

  Agent 需要在 Pro Expense 应用中记录一笔消费，
  名字是 shopping，金额是 936.99 元。
  验证方式：使用 LLM 判断记账记录是否符合要求。
  """

  app_name = "pro expense"

  complexity = 4.0

  _EXPENSE_NAME = "shopping"
  _EXPENSE_AMOUNT = 93699  # 936.99元，单位：分
  _CATEGORY = "Others"
  _SNAPSHOT_NAME = "snapshot_11_medium"

  @property
  def goal(self) -> str:
    return f"Please record my online shopping expense in {self.app_name} app, name it {self._EXPENSE_NAME}, category is {self._CATEGORY}."

  @property
  def full_goal(self) -> str:
    return f"Record an expense in {self.app_name} app named '{self._EXPENSE_NAME}' with amount 936.99 yuan and category '{self._CATEGORY}'."

  @property
  def information(self) -> str:
    return "I bought some products on jingdian and taodian apps."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_expenses = expense_validator.get_expenses(env)
    print(f"[DEBUG] Initializing expense record shopping task...")
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


class User11Medium_ExpenseRecordTransfer(fixed_task_eval.TaskEval):
  """固定任务：在 Pro Expense 中记录转账收入。

  Agent 需要在 Pro Expense 应用中记录一笔转账收入，
  名字是 transfer，金额是 2400 元。
  验证方式：使用 LLM 判断记账记录是否符合要求。
  """

  app_name = "pro expense"

  complexity = 4.0

  _EXPENSE_NAME = "transfer"
  _EXPENSE_AMOUNT = 240000  # 2400元，单位：分
  _CATEGORY = "Income"
  _SNAPSHOT_NAME = "snapshot_11_medium"

  @property
  def goal(self) -> str:
    return f"A friend transferred money to me. Please record it in {self.app_name} app, name it {self._EXPENSE_NAME}."

  @property
  def full_goal(self) -> str:
    return f"Record an income in {self.app_name} app named '{self._EXPENSE_NAME}' with amount 2400 yuan."

  @property
  def information(self) -> str:
    return "Thomas Anderson texted me via simple sms messenger app saying he transferred money to me."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_expenses = expense_validator.get_expenses(env)
    print(f"[DEBUG] Initializing expense record transfer task...")
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


class User11Medium_CalendarModifyGroupMeeting(fixed_task_eval.TaskEval):
  """固定任务：修改 Group meeting 日程时间。

  Agent 需要在日历应用中将 5 月 7 日的 Group meeting 修改到 5 月 6 日下午 4 点。
  验证方式：检查日历事件的时间是否被正确修改。
  """

  app_name = "simple calendar"

  complexity = 4.0

  _EVENT_TITLE = "Group meeting"
  _NEW_START_TS = 1778083200  # 2026-05-06 16:00:00 UTC
  _SNAPSHOT_NAME = "snapshot_11_medium"

  @property
  def goal(self) -> str:
    return f"Modify the group meeting time in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Modify the {self._EVENT_TITLE} event from May 7th to May 6th at 4:00 PM in {self.app_name} app."

  @property
  def information(self) -> str:
    return "Mary Brown texted me via simple sms messenger app saying the meeting time has changed."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_events = calendar_validator.get_current_events(env)
    print(f"[DEBUG] Initializing calendar modify group meeting task...")
    print(f"[DEBUG] Before events: {len(self._before_events)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_events'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = calendar_validator.validate_event_time_modified(
        env=env,
        before_events=self._before_events,
        expected_title=self._EVENT_TITLE,
        expected_start_ts=self._NEW_START_TS,
    )
    return 1.0 if result else 0.0


class User11Medium_TasksCreateCallPhone(fixed_task_eval.TaskEval):
  """固定任务：创建待办提醒晚上打电话。

  Agent 需要在 Tasks 应用中创建一个待办，
  提醒晚上 7 点打电话给 13988665523。
  验证方式：检查待办是否被正确创建。
  """

  app_name = "tasks"

  complexity = 4.0

  _TASK_TITLE = "Call 13988665523"
  _DUE_DATE_TS = 1777665601000  # 2026-05-31 19:00:00 UTC
  _SNAPSHOT_NAME = "snapshot_11_medium"

  @property
  def goal(self) -> str:
    return f"Create a todo in {self.app_name} app, reminding me to call the number I answered this morning at 8 PM."

  @property
  def full_goal(self) -> str:
    return f"Create a todo in {self.app_name} app with title '{self._TASK_TITLE}', due at 8 PM."

  @property
  def information(self) -> str:
    return "I answered a phone call from a number starting with 139 this morning."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_tasks = task_validator.get_tasks(env)
    print(f"[DEBUG] Initializing tasks create call phone task...")
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


