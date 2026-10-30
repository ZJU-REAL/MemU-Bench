"""固定任务：长任务集合。

包含以下任务：
- User11Long_JingdianOrderCola: 在京店下单两箱罐装可乐
- User11Long_TasksPreheatOven: 创建预热烤箱待办
- User11Long_ExpenseRecordAlipay: 在 Pro Expense 中记录支付宝消费
- User11Long_SMSSendPaperRecommendation: 给 Sarah Jones 推荐论文
- User11Long_TasksCompleteMultiple: 将多个待办标记为已完成
- User11Long_ExpenseDeleteLendMoney: 删除借钱给 Sarah Jones 的记录
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import expense as expense_validator
from android_world.task_evals.custom_validators import jingdian as jingdian_validator
from android_world.task_evals.custom_validators import sms as sms_validator
from android_world.task_evals.custom_validators import task as task_validator


class User11Long_JingdianOrderCola(fixed_task_eval.TaskEval):
  """固定任务：在京店下单两箱罐装可乐。

  Agent 需要在京店应用中下单两箱罐装可乐。
  验证方式：比较操作前后的订单，检查是否有匹配的新订单。
  """

  app_name = "jingdian"

  complexity = 4.0

  _PRODID = '102'
  _SKUID = '102002'
  _SHOPID = '1'
  _PROD_COUNT = 2
  _SNAPSHOT_NAME = "snapshot_11_long"

  @property
  def goal(self) -> str:
    return f"The cola I ordered before is not enough, please order two more boxes of that cola on {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Order two boxes of canned cola on {self.app_name} app. Payment password is 123456"

  @property
  def information(self) -> str:
    return "I ordered cola on jingdian app before."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_orders = jingdian_validator.get_orders(env)
    print(f"[DEBUG] Initializing jingdian order cola task...")
    print(f"[DEBUG] Before orders: {len(self._before_orders)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_orders'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = jingdian_validator.validate_order_created(
        env=env,
        before_orders=self._before_orders,
        expected={
            'prodId': self._PRODID,
            'skuId': self._SKUID,
            'shopId': self._SHOPID,
            'prodCount': self._PROD_COUNT,
        },
        save_img_path=self.save_img_path,
        goal=self.full_goal,
    )
    return 1.0 if result else 0.0


class User11Long_TasksPreheatOven(fixed_task_eval.TaskEval):
  """固定任务：创建预热烤箱待办。

  Agent 需要在 Tasks 应用中创建一个待办，
  标题是预热烤箱到 180°C。
  验证方式：检查待办是否被正确创建。
  """

  app_name = "tasks"

  complexity = 4.0

  _TASK_TITLE = "Preheat oven to 180°C"
  _SNAPSHOT_NAME = "snapshot_11_long"

  @property
  def goal(self) -> str:
    return f"I want to make honey cake. Please add a todo in {self.app_name} app, the title is preheat oven, I don't remember the temperature."

  @property
  def full_goal(self) -> str:
    return f"Create a todo in {self.app_name} app with title '{self._TASK_TITLE}'."

  @property
  def information(self) -> str:
    return "The broccoli app has the oven temperature recorded."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_tasks = task_validator.get_tasks(env)
    print(f"[DEBUG] Initializing tasks preheat oven task...")
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
    )
    return 1.0 if result else 0.0


class User11Long_ExpenseRecordAlipay(fixed_task_eval.TaskEval):
  """固定任务：在 Pro Expense 中记录支付宝消费。

  Agent 需要在 Pro Expense 应用中记录一笔消费，
  名字是 Alipay consumption，金额是 194 元，类别是 Others。
  验证方式：使用 LLM 判断记账记录是否符合要求。
  """

  app_name = "pro expense"

  complexity = 4.0

  _EXPENSE_NAME = "Alipay consumption"
  _EXPENSE_AMOUNT = 19400  # 194元，单位：分
  _CATEGORY = "Others"
  _SNAPSHOT_NAME = "snapshot_11_long"

  @property
  def goal(self) -> str:
    return f"Please record a bill in {self.app_name}, name it {self._EXPENSE_NAME}, the total amount is the total spending using Alipay today."

  @property
  def full_goal(self) -> str:
    return f"Record an expense in {self.app_name} app named '{self._EXPENSE_NAME}' with amount 194 yuan and category '{self._CATEGORY}'."

  @property
  def information(self) -> str:
    return "I used Alipay to order some items on jingdian, taodian, and tuantuanwaimai today."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_expenses = expense_validator.get_expenses(env)
    print(f"[DEBUG] Initializing expense record alipay task...")
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


class User11Long_SMSSendPaperRecommendation(fixed_task_eval.TaskEval):
  """固定任务：给 Sarah Jones 推荐论文。

  Agent 需要在 Simple SMS Messenger 中给 Sarah Jones 发短信，
  推荐 Android World 这篇论文。
  验证方式：检查短信数据库中是否有发送给目标号码的短信，且内容匹配。
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  _CONTACT_NAME = "Sarah Jones"
  _PHONE_NUMBER = "5556635514"
  _MESSAGE_BODY = "I recommend you read the paper 'AndroidWorld', it's very informative."
  _PAPER_NAME = "AndroidWorld"
  _SNAPSHOT_NAME = "snapshot_11_long"

  @property
  def goal(self) -> str:
    return f"Send a text message to {self._CONTACT_NAME} via {self.app_name} app, recommending the paper I read the most today."

  @property
  def full_goal(self) -> str:
    return f"Send a text message to {self._CONTACT_NAME} via {self.app_name} app, recommending the paper '{self._PAPER_NAME}'."

  @property
  def information(self) -> str:
    return "The paper I read today has 'Android' in its title."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing SMS send paper recommendation task...")
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


class User11Long_TasksCompleteMultiple(fixed_task_eval.TaskEval):
  """固定任务：将多个待办标记为已完成。

  Agent 需要在 Tasks 应用中将买可乐和买 T-shirt 的待办标记为已完成。
  验证方式：检查待办是否被标记为完成。
  """

  app_name = "tasks"

  complexity = 4.0

  _TASK_TITLES = ["By some coco cola 🥤", "Buy one T-shirt"]
  _SNAPSHOT_NAME = "snapshot_11_long"

  def __init__(self):
    super().__init__()
    self._before_tasks = None

  @property
  def goal(self) -> str:
    return f"I completed some tasks today, please mark them as completed in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Mark the tasks '{self._TASK_TITLES[0]}' and '{self._TASK_TITLES[1]}' as completed in {self.app_name} app."

  @property
  def information(self) -> str:
    return "I bought cola and T-shirt today."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_tasks = task_validator.get_tasks(env)
    print(f"[DEBUG] Initializing tasks complete multiple task...")
    print(f"[DEBUG] Before tasks: {len(self._before_tasks)}")
    for task in self._before_tasks:
      print(f"[DEBUG]   - {task.title} (completed: {task.completed})")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if self._before_tasks is None:
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = task_validator.validate_tasks_completed(
        env=env,
        before_tasks=self._before_tasks,
        task_titles=self._TASK_TITLES,
    )
    return 1.0 if result else 0.0


class User11Long_ExpenseDeleteLendMoney(fixed_task_eval.TaskEval):
  """固定任务：删除借钱给 Sarah Jones 的记录。

  Agent 需要在 Pro Expense 应用中删除借钱给 Sarah Jones 的记录。
  验证方式：检查记账记录是否被正确删除。
  """

  app_name = "pro expense"

  complexity = 4.0

  _EXPENSE_NAME = "Lend to Sarah Jones"
  _SNAPSHOT_NAME = "snapshot_11_long"

  def __init__(self):
    super().__init__()
    self._before_expenses = None

  @property
  def goal(self) -> str:
    return f"A friend paid me back, please delete the lending record in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Delete the expense record named '{self._EXPENSE_NAME}' in {self.app_name} app."

  @property
  def information(self) -> str:
    return "Sarah Jones texted me via simple sms messenger app saying she paid me back."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_expenses = expense_validator.get_expenses(env)
    print(f"[DEBUG] Initializing expense delete lend money task...")
    print(f"[DEBUG] Before expenses: {len(self._before_expenses)}")
    for exp in self._before_expenses:
      print(f"[DEBUG]   - {exp.name}: {exp.amount}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if self._before_expenses is None:
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = expense_validator.validate_expense_deleted(
        env=env,
        before_expenses=self._before_expenses,
        expense_name=self._EXPENSE_NAME,
    )
    return 1.0 if result else 0.0