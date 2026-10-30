

"""固定任务：中等任务集合。

包含以下任务：
- SMSSendToWilliam: 给 William Smith 发短信询问周末去 Yuma 还是 Indio
- ExpenseRecordCola: 在 Pro Expense 中记录可乐消费
- TasksCreateReminder: 在 Tasks 中创建催款待办
- GalleryRenameReceipt: 在 Simple Gallery 中重命名收据图片
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import expense as expense_validator
from android_world.task_evals.custom_validators import files as files_validator
from android_world.task_evals.custom_validators import sms as sms_validator
from android_world.task_evals.custom_validators import task as task_validator


class User5Medium_SMSSendToWilliam(fixed_task_eval.TaskEval):
  """固定任务：给 William Smith 发短信询问周末去 Yuma 还是 Indio。

  Agent 需要在 Simple SMS Messenger 中给 William Smith 发送短信，
  询问周末去 Yuma 还是 Indio。
  验证方式：检查短信数据库中是否有发送给目标号码的短信，且内容匹配。
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  _CONTACT_NAME = "William Smith"
  _PHONE_NUMBER = "5552435958"
  _MESSAGE_BODY = "Do you know whether we’re going to Yuma or Indio this weekend?"
  _SNAPSHOT_NAME = "snapshot_5_medium"

  @property
  def goal(self) -> str:
    return f"I marked two places on the map. Send a text message to William Smith asking which of these two places we should go to this weekend via {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Send a text message to {self._CONTACT_NAME} via {self.app_name} app, asking '{self._MESSAGE_BODY}'"

  @property
  def information(self):
    return "I marked two locations in the OsmAnd app."

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


class User5Medium_ExpenseRecordCola(fixed_task_eval.TaskEval):
  """固定任务：在 Pro Expense 中记录可乐消费。

  Agent 需要在 Pro Expense 应用中记录一笔消费，
  名字是可乐，金额是 19.5 元，类别是 food。
  验证方式：使用 LLM 判断记账记录是否符合要求。
  """

  app_name = "pro expense"

  complexity = 4.0

  _EXPENSE_NAME = "cola"
  _EXPENSE_AMOUNT = 1950  # 19.5元，单位：分
  _CATEGORY = "Food"
  _SNAPSHOT_NAME = "snapshot_5_medium"

  @property
  def goal(self) -> str:
    return f"Please record my previous expenses on buying cola online in {self.app_name}, name it cola, and set the category to food."

  @property
  def full_goal(self) -> str:
    return f"Record an expense in {self.app_name} app named '{self._EXPENSE_NAME}' with amount 19.5 yuan and category '{self._CATEGORY}'."

  @property
  def information(self):
    return "I bought some bottled and canned cola on jingdian app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_expenses = expense_validator.get_expenses(env)
    print(f"[DEBUG] Initializing expense record cola task...")
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


class User5Medium_TasksCreateReminder(fixed_task_eval.TaskEval):
  """固定任务：在 Tasks 中创建催款待办。

  Agent 需要在 Tasks 应用中创建一个催款待办，
  名字是催款，截止日期是5月15日，内容是催 David Johnson 还钱。
  验证方式：使用 LLM 判断待办内容是否符合要求。
  """

  app_name = "tasks"

  complexity = 4.0

  _TASK_TITLE = "Debt Collection"
  _TASK_NOTES = "Remind David Johnson to repay the money"
  _DUE_DATE = "2026-05-15"
  _DUE_DATE_TS = 1778846400000  # 2026-05-15
  _SNAPSHOT_NAME = "snapshot_5_medium"

  @property
  def goal(self) -> str:
    return f"Create a todo in {self.app_name} app named '{self._TASK_TITLE}' with due date {self._DUE_DATE}, reminding the person who owes me money to pay back."

  @property
  def full_goal(self) -> str:
    return f"Create a todo in {self.app_name} app named '{self._TASK_TITLE}' with due date {self._DUE_DATE}, notes: {self._TASK_NOTES}."

  @property
  def information(self):
    return f"I recorded in expense pro app that someone owes me money."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_tasks = task_validator.get_tasks(env)
    print(f"[DEBUG] Initializing tasks create reminder task...")
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
        expected_notes=self._TASK_NOTES,
        expected_due_date=self._DUE_DATE_TS,
    )
    return 1.0 if result else 0.0


class User5Medium_GalleryRenameReceipt(fixed_task_eval.TaskEval):
  """固定任务：在 Simple Gallery 中重命名收据图片。

  Agent 需要在 Simple Gallery Pro 中将 receipt_001.jpg 重命名为 technology.jpg。
  验证方式：检查文件系统中原文件是否已不存在，新文件是否存在。
  """

  app_name = "simple gallery"

  complexity = 4.0

  _OLD_FILE_NAME = "receipt_005.jpg"
  _NEW_FILE_NAME = "technology.jpg"
  _FILE_DIRECTORY = "/sdcard/DCIM"
  _SNAPSHOT_NAME = "snapshot_5_medium"

  @property
  def goal(self) -> str:
    return f"Rename the last receipt I viewed to 'technology' in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Rename {self._OLD_FILE_NAME} to {self._NEW_FILE_NAME} in {self.app_name} app."

  @property
  def information(self):
    return f"There is a wireless mouse on the receipt."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing gallery rename receipt task...")
    print(f"[DEBUG] Target: {self._OLD_FILE_NAME} -> {self._NEW_FILE_NAME}")
    print(f"[DEBUG] Directory: {self._FILE_DIRECTORY}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = files_validator.validate_file_renamed(
        env=env,
        old_name=self._OLD_FILE_NAME,
        new_name=self._NEW_FILE_NAME,
        directory_path=self._FILE_DIRECTORY,
    )
    return 1.0 if result else 0.0
