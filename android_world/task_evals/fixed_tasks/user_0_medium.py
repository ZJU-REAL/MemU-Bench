

"""固定任务：中等任务集合。

包含以下任务：
- TasksCompletePaper: 在 Tasks 中标记论文阅读待办为完成
- CalendarAddEvent: 在日历中添加活动日程
- ContactsAddFromCard: 在 Contacts 中添加名片联系人
- PhoneCallFromCard: 拨打名片上的电话号码
- ExpenseRecordOuting: 在 Pro Expense 中记录 outing 消费
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import calendar as calendar_validator
from android_world.task_evals.custom_validators import contacts as contacts_validator
from android_world.task_evals.custom_validators import expense as expense_validator
from android_world.task_evals.custom_validators import phone as phone_validator
from android_world.task_evals.custom_validators import task as task_validator


class User0Medium_TasksCompletePaper(fixed_task_eval.TaskEval):
  """固定任务：在 Tasks 中标记论文阅读待办为完成。

  Agent 需要在 Tasks 应用中将 "read paper attention is all you need" 标记为完成。
  验证方式：检查任务是否被标记为完成状态。
  """

  app_name = "tasks"

  complexity = 4.0

  _TASK_TITLE = "Reading paper: Attention is all you need"
  _SNAPSHOT_NAME = "snapshot_0_medium"

  @property
  def goal(self) -> str:
    return f"Mark the recently finished to-do item as completed for me in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Mark the task '{self._TASK_TITLE}' as completed in {self.app_name} app."

  @property
  def information(self):
    return "I finished reading a paper."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_tasks = task_validator.get_tasks(env)
    print(f"[DEBUG] Initializing tasks complete paper task...")
    print(f"[DEBUG] Before tasks: {len(self._before_tasks)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_tasks'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = task_validator.validate_task_completed(
        env=env,
        before_tasks=self._before_tasks,
        task_title=self._TASK_TITLE,
    )
    return 1.0 if result else 0.0


class User0Medium_CalendarAddEvent(fixed_task_eval.TaskEval):
  """固定任务：在日历中添加活动日程。

  Agent 需要在 Simple Calendar Pro 中添加一个活动日程，
  根据相册中看到的活动信息填写标题、地点和时间。
  验证方式：比较任务执行前后的数据库状态，检查新增事件是否匹配。
  """

  app_name = "simple calendar"

  complexity = 4.0

  _EVENT_TITLE = "Annual Tech Conference"
  _EVENT_LOCATION = "Downtown Plaza"
  _EVENT_START_TS = 1778100300   # 2026-05-06 20:45:00 UTC
  _EVENT_END_TS = 1778103900     # 2026-05-06 21:45:00 UTC
  _SNAPSHOT_NAME = "snapshot_0_medium"

  @property
  def goal(self) -> str:
    return (
      "I saw a picture earlier that contains information about an event."
      f"Please help me create a schedule in {self.app_name} app, including the title, location, start and end time. The event is supposed to last for one hour."
    )

  @property
  def full_goal(self) -> str:
    return f"Add an event titled '{self._EVENT_TITLE}' at {self._EVENT_LOCATION} from 20:45 to 21:45 on May 6 in {self.app_name} app."

  @property
  def information(self):
    return "I viewed an image in Simple Gallery app, which shows the event title: Annual Tech Conference."

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


class User0Medium_ContactsAddFromCard(fixed_task_eval.TaskEval):
  """固定任务：在 Contacts 中添加名片联系人。

  Agent 需要在 Contacts 应用中添加一个联系人，
  根据相册中看到的名片信息填写姓名、号码和邮箱。
  验证方式：比较任务执行前后的联系人列表，检查新增联系人是否匹配。
  """

  app_name = "contacts"

  complexity = 4.0

  _CONTACT_NAME = "Richard Williams"
  _CONTACT_NUMBER = "4045231666"
  _CONTACT_EMAIL = "richard.williams94@apextech.com"
  _SNAPSHOT_NAME = "snapshot_0_medium"

  @property
  def goal(self) -> str:
    return f"Add the business card I just viewed to contacts in {self.app_name} app, and save the name, phone number and email address."

  @property
  def full_goal(self) -> str:
    return f"Add {self._CONTACT_NAME} to contacts with phone number {self._CONTACT_NUMBER} and email {self._CONTACT_EMAIL} in {self.app_name} app."

  @property
  def information(self):
    return "I just saw a business card in the Simple Gallery app. The person's name seems to be Richard Williams."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_contacts = contacts_validator.get_contacts(env)
    print(f"[DEBUG] Initializing contacts add from card task...")
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
        expected_email=self._CONTACT_EMAIL,
    )
    return 1.0 if result else 0.0


class User0Medium_PhoneCallFromCard(fixed_task_eval.TaskEval):
  """固定任务：拨打名片上的电话号码。

  Agent 需要拨打名片上的电话号码。
  验证方式：检查拨号器界面是否显示了正确的号码。
  """

  app_name = "phone"

  complexity = 4.0

  _CONTACT_NAME = "Richard Williams"
  _PHONE_NUMBER = "4045231666"
  _SNAPSHOT_NAME = "snapshot_0_medium"

  @property
  def goal(self) -> str:
    return f"I just saw a business card. Please call the person on it using {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Call {self._PHONE_NUMBER} using {self.app_name} app."

  @property
  def information(self):
    return "I just saw a business card in the Simple Gallery app. The person's name seems to be Richard Williams."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing phone call from card task...")
    print(f"[DEBUG] Target: {self._CONTACT_NAME} ({self._PHONE_NUMBER})")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = phone_validator.called_correct_number(
        env=env,
        phone_number=self._PHONE_NUMBER,
        contact_name=self._CONTACT_NAME,
    )
    return 1.0 if result else 0.0


class User0Medium_ExpenseRecordOuting(fixed_task_eval.TaskEval):
  """固定任务：在 Pro Expense 中记录 outing 消费。

  Agent 需要在 Pro Expense 应用中记录一笔消费，
  标题是 outing，金额是 124.5 元，类别是 social。
  验证方式：使用 LLM 判断记账记录是否符合要求。
  """

  app_name = "pro expense"

  complexity = 4.0

  _EXPENSE_NAME = "outing"
  _EXPENSE_AMOUNT = 12450  # 124.5元，单位：分
  _CATEGORY = "Social"
  _SNAPSHOT_NAME = "snapshot_0_medium"

  @property
  def goal(self) -> str:
    return f"I calculated my expenses, please record it in the {self.app_name} app, name it outing, and set the category to social."

  @property
  def full_goal(self) -> str:
    return f"Record an expense named '{self._EXPENSE_NAME}' with amount 124.5 yuan and category '{self._CATEGORY}' in {self.app_name} app."

  @property
  def information(self):
    return "I calculated the expenses using the calculator."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_expenses = expense_validator.get_expenses(env)
    print(f"[DEBUG] Initializing expense record outing task...")
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