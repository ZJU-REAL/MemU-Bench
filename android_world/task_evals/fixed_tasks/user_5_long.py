

"""固定任务：长任务集合。

包含以下任务：
- SMSSendDeliveryDriverPhone: 给 Sarah Jones 发送配送员电话号码
- TasksUpdateMaryJones: 删除旧待办并创建新待办
- TasksCreateGuitarPractice: 创建吉他练习待办
- TaodianOrderTShirt: 在淘店购买运动透气性T恤
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import sms as sms_validator
from android_world.task_evals.custom_validators import taodian as taodian_validator
from android_world.task_evals.custom_validators import task as task_validator


class User5Long_SMSSendDeliveryDriverPhone(fixed_task_eval.TaskEval):
  """固定任务：给 Sarah Jones 发送配送员电话号码。

  Agent 需要在 Simple SMS Messenger 中给 Sarah Jones 发送短信，
  内容是外卖配送员电话号码：17907938000。
  验证方式：检查短信数据库中是否有发送给目标号码的短信，且内容匹配。
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  _CONTACT_NAME = "Sarah Jones"
  _PHONE_NUMBER = "5556635514"
  _MESSAGE_BODY = "Delivery driver phone number: 17907938000"
  _SNAPSHOT_NAME = "snapshot_5_long"

  @property
  def goal(self) -> str:
    return f"Send the new driver's phone number to {self._CONTACT_NAME} via {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Send a text message to {self._CONTACT_NAME} via {self.app_name} app, saying '{self._MESSAGE_BODY}'"

  @property
  def information(self):
    return f"The new delivery driver texted me their phone number via {self.app_name} app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing SMS send delivery driver phone task...")
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


class User5Long_TasksUpdateMaryJones(fixed_task_eval.TaskEval):
  """固定任务：删除旧的 Mary Jones 待办并创建新的待办。

  Agent 需要在 Tasks 应用中删除 "Help Mary Jones pay 15 yuan" 待办，
  并创建一个新的待办，名字是 "Help Mary Jones pay 20 yuan"，截止日期是5月12日。
  验证方式：检查旧待办是否被删除，新待办是否被创建。
  """

  app_name = "tasks"

  complexity = 4.0

  _OLD_TASK_TITLE = "Help Mary Jones pay 15 yuan"
  _NEW_TASK_TITLE = "Help Mary Jones pay 20 yuan"
  _NEW_TASK_NOTES = "Pay 20 yuan to Mary Jones"
  _NEW_DUE_DATE = "2026-05-12"
  _NEW_DUE_DATE_TS = 1778587200000  # 2026-05-12
  _SNAPSHOT_NAME = "snapshot_5_long"

  @property
  def goal(self) -> str:
    return f"Delete the todo for paying Mary Jones and create a new one with updated amount in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Delete the todo named '{self._OLD_TASK_TITLE}' and create a new todo named '{self._NEW_TASK_TITLE}' with due date {self._NEW_DUE_DATE} in {self.app_name} app."

  @property
  def information(self):
    return "Mary Jones texted me via simple sms messenger app that the plan has changed."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_tasks = task_validator.get_tasks(env)
    print(f"[DEBUG] Initializing tasks update Mary Jones task...")
    print(f"[DEBUG] Before tasks: {len(self._before_tasks)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_tasks'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    # 先验证旧任务是否被删除
    delete_result = task_validator.validate_task_deleted(
        env=env,
        before_tasks=self._before_tasks,
        task_title=self._OLD_TASK_TITLE,
    )

    if not delete_result:
      print("[DEBUG] Old task not deleted, validation failed")
      return 0.0

    # 再验证新任务是否被创建
    add_result = task_validator.validate_task_added(
        env=env,
        goal=self.full_goal,
        before_tasks=self._before_tasks,
        expected_title=self._NEW_TASK_TITLE,
        expected_notes=self._NEW_TASK_NOTES,
        expected_due_date=self._NEW_DUE_DATE_TS,
    )

    return 1.0 if add_result else 0.0


class User5Long_TasksCreateGuitarPractice(fixed_task_eval.TaskEval):
  """固定任务：在 Tasks 中创建吉他练习待办。

  Agent 需要在 Tasks 应用中创建一个吉他练习待办，
  名字是吉他练习，内容是练习Forever Young歌曲的吉他演奏。
  验证方式：使用 LLM 判断待办内容是否符合要求。
  """

  app_name = "tasks"

  complexity = 4.0

  _TASK_TITLE = "Guitar Practice"
  _TASK_NOTES = "Practice guitar performance of Forever Young"
  _SNAPSHOT_NAME = "snapshot_5_long"

  @property
  def goal(self) -> str:
    return f"Create a todo in {self.app_name} app named '{self._TASK_TITLE}', the content is about practicing the guitar performance of the song we agreed on."

  @property
  def full_goal(self) -> str:
    return f"Create a todo in {self.app_name} app named '{self._TASK_TITLE}' with notes: {self._TASK_NOTES}."

  @property
  def information(self):
    return "I confirmed with Barbara Jones via simple sms messenger app about which song to perform."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_tasks = task_validator.get_tasks(env)
    print(f"[DEBUG] Initializing tasks create guitar practice task...")
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
    )
    return 1.0 if result else 0.0


class User5Long_TaodianOrderTShirt(fixed_task_eval.TaskEval):
  """固定任务：在 Taodian 购买运动透气性T恤。

  Agent 需要在 Taodian 淘店中购买运动透气性T恤。
  验证方式：比较任务执行前后的订单数据，检查新订单是否匹配。
  """

  app_name = "taodian"

  complexity = 4.0

  _PROD_NAME = "运动透气性T恤"
  _SKU_NAME = "M码"
  _PRODID = "2"
  _SKUID = "2002"
  _SHOPID = "1"
  _PROD_COUNT = 1
  _SNAPSHOT_NAME = "snapshot_5_long"

  @property
  def goal(self) -> str:
    return f"Buy the T-shirt I mentioned earlier in {self.app_name} app. The payment password is 123456."

  @property
  def full_goal(self) -> str:
    return f"Buy the {self._PROD_NAME} in {self.app_name} app, size {self._SKU_NAME}. The payment password is 123456."

  @property
  def information(self):
    return "I chatted with Thomas Anderson via simple sms messenger app about clothes."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_orders = taodian_validator.get_orders(env)
    print(f"[DEBUG] Initializing taodian order t-shirt task...")
    print(f"[DEBUG] Before orders: {len(self._before_orders)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_orders'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = taodian_validator.validate_order_created(
        env=env,
        before_orders=self._before_orders,
        expected={
            'prodId': self._PRODID,
            'skuId': self._SKUID,
            'shopId': self._SHOPID,
            'skuName': self._SKU_NAME,
            'prodCount': self._PROD_COUNT,
        },
    )
    return 1.0 if result else 0.0