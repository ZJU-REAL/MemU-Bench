

"""固定任务：中等任务集合。

包含以下任务：
- TuantuanOrderBurgers: 在美味汉堡王下单汉堡并添加备注
- TasksCreateBirthdayWish: 创建生日祝福待办
- SMSSendShoppingList: 分享购物清单给 Mary Brown
- SMSSendDebtReminder: 给 Jennifer Smith 发送欠款提醒
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import sms as sms_validator
from android_world.task_evals.custom_validators import task as task_validator
from android_world.task_evals.custom_validators import tuantuan as tuantuan_validator


class User6Medium_TuantuanOrderBurgers(fixed_task_eval.TaskEval):
  """固定任务：在美味汉堡王下单汉堡并添加备注。

  Agent 需要在 Tuantuan 外卖应用中下单一个香辣鸡腿堡和一个双层牛肉堡，
  并添加备注：Make the Spicy Chicken Leg Burger mildly spicy;
  for the Double Beef Burger, add extra cheese and omit lettuce.
  验证方式：比较任务执行前后的订单数据，检查新订单是否匹配。
  """

  app_name = "tuantuanwaimai"

  complexity = 4.0

  _SHOP_NAME = "美味汉堡王"
  _FOOD_1_NAME = "香辣鸡腿堡"
  _FOOD_2_NAME = "双层牛肉堡"
  _REMARK = "Make the Spicy Chicken Leg Burger mildly spicy; for the Double Beef Burger, add extra cheese and omit lettuce."
  _SNAPSHOT_NAME = "snapshot_6_medium"

  @property
  def goal(self) -> str:
    return f"Order the burger I recorded before on {self.app_name} app and add the remarks."

  @property
  def full_goal(self) -> str:
    return f"Order one {self._FOOD_1_NAME} and one {self._FOOD_2_NAME} from {self._SHOP_NAME} on {self.app_name} app, with remark: '{self._REMARK}'."

  @property
  def information(self):
    return "I have a note about a burger recorded in Joplin."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_orders = tuantuan_validator.get_orders(env)
    print(f"[DEBUG] Initializing tuantuan order burgers task...")
    print(f"[DEBUG] Before orders: {len(self._before_orders)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_orders'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = tuantuan_validator.validate_orders_created(
        env=env,
        before_orders=self._before_orders,
        expected={
            'orders': [
                {
                    'shop_name': self._SHOP_NAME,
                    'foods': [
                        {'name': self._FOOD_1_NAME},
                        {'name': self._FOOD_2_NAME},
                    ],
                    'remark': self._REMARK,
                }
            ]
        },
    )
    return 1.0 if result else 0.0


class User6Medium_TasksCreateBirthdayWish(fixed_task_eval.TaskEval):
  """固定任务：在 Tasks 中创建生日祝福待办。

  Agent 需要在 Tasks 应用中创建一个待办，
  内容是给 Jennifer Smith 送生日祝福，日期是5月22日。
  验证方式：使用 LLM 判断待办内容是否符合要求。
  """

  app_name = "tasks"

  complexity = 4.0

  _TASK_TITLE = "Send birthday wishes to Jennifer Smith"
  _DUE_DATE = "2026-05-22"
  _DUE_DATE_TS = 1779451200000  # 2026-05-22
  _SNAPSHOT_NAME = "snapshot_6_medium"

  @property
  def goal(self) -> str:
    return f"Create a todo in {self.app_name} app to send birthday wishes to Jennifer Smith."

  @property
  def full_goal(self) -> str:
    return f"Create a todo in {self.app_name} app with content '{self._TASK_TITLE}' and due date {self._DUE_DATE}."

  @property
  def information(self):
    return "Mary Brown texted me Jennifer Smith's birthday via simple sms messenger app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_tasks = task_validator.get_tasks(env)
    print(f"[DEBUG] Initializing tasks create birthday wish task...")
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


class User6Medium_SMSSendShoppingList(fixed_task_eval.TaskEval):
  """固定任务：分享购物清单给 Mary Brown。

  Agent 需要在 Simple SMS Messenger 中给 Mary Brown 发送短信，
  内容是 Joplin 中记录的 shopping list。
  验证方式：检查短信数据库中是否有发送给目标号码的短信，且内容匹配。
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  _CONTACT_NAME = "Mary Brown"
  _PHONE_NUMBER = "5556136850"
  _MESSAGE_BODY = '''6.Shopping list
1 1.A modern minimalist sofa
2.A classic white men's T-shirt
3.A hydrating face cream set
4.Two MacBook Pros
5.A smartwatch'''
  _SNAPSHOT_NAME = "snapshot_6_medium"

  @property
  def goal(self) -> str:
    return f"Share my recorded shopping list with Mary Brown via {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Send the shopping list from Joplin to {self._CONTACT_NAME} via {self.app_name} app."

  @property
  def information(self):
    return "I recorded a shopping list in Joplin."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing SMS send shopping list task...")
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


class User6Medium_SMSSendDebtReminder(fixed_task_eval.TaskEval):
  """固定任务：给 Jennifer Smith 发送欠款提醒。

  Agent 需要在 Simple SMS Messenger 中给 Jennifer Smith 发送短信，
  内容是提醒她欠款 150 元并询问何时归还。
  验证方式：检查短信数据库中是否有发送给目标号码的短信，且内容匹配。
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  _CONTACT_NAME = "Jennifer Smith"
  _PHONE_NUMBER = "5552200678"
  _MESSAGE_BODY = "You owe me 150 yuan, when will you pay me back?"
  _SNAPSHOT_NAME = "snapshot_6_medium"

  @property
  def goal(self) -> str:
    return f"Send a text message to my friend, telling her how much she owes me and ask when she will pay me back via {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Send a text message to {self._CONTACT_NAME} via {self.app_name} app, saying '{self._MESSAGE_BODY}'"

  @property
  def information(self):
    return "Pro expense recorded this debt."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing SMS send debt reminder task...")
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