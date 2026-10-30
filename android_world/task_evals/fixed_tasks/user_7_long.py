

"""固定任务：长任务集合。

包含以下任务：
- TaodianOrderDress: 在淘店购买女士蕾丝花卉鸡尾酒连衣裙
- User7Long_SMSSendQuoteToContact: 给 Barbara Jones 发送 Joplin 中记录的名言
- User7Long_JingdianOrderCola: 在京店下单两箱罐装无糖可乐
- User7Long_TasksCreateShoppingList: 添加采购食材的待办
- User7Long_SMSSendFoodDelivery: 给 Mary Brown 发短信询问外卖是否收到
- User7Long_OpenSolitairecg: 打开 solitairecg 游戏
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import app_opened as app_opened_validator
from android_world.task_evals.custom_validators import jingdian as jingdian_validator
from android_world.task_evals.custom_validators import sms as sms_validator
from android_world.task_evals.custom_validators import task as task_validator
from android_world.task_evals.custom_validators import taodian as taodian_validator


class User7Long_TaodianOrderDress(fixed_task_eval.TaskEval):
  """固定任务：在淘店购买女士蕾丝花卉鸡尾酒连衣裙。

  Agent 需要在 Taodian 淘店中购买一件 S 码的女士蕾丝花卉鸡尾酒连衣裙，
  联系人填 Zhao Si，号码填 13121461717，
  地址是 Building 1, Yard 56, Chaoyang North Road。
  验证方式：比较任务执行前后的订单数据，检查新订单是否匹配。
  """

  app_name = "taodian"

  complexity = 4.0

  _PROD_NAME = "女士蕾丝花卉鸡尾酒连衣裙"
  _PROD_ID='25'
  _SKUID='25001'
  _SHOPID='1'
  _PROD_COUNT = 1
  _CONTACT_NAME = "Zhao Si"
  _PHONE = "13121461717"
  _ADDRESS = "Building 1, Yard 56, Chaoyang North Road"
  _SNAPSHOT_NAME = "snapshot_7_long"

  @property
  def goal(self) -> str:
    return f"Buy one {self._PROD_NAME} on {self.app_name} app for {self._CONTACT_NAME}. Payment password is 123456."

  @property
  def full_goal(self) -> str:
    return f"Buy one {self._PROD_NAME} on {self.app_name} app, contact name is {self._CONTACT_NAME}, phone number is {self._PHONE}, address is {self._ADDRESS}. Payment password is 123456."

  @property
  def information(self):
    return "She texted me the address via simple sms messenger app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_orders = taodian_validator.get_orders(env)
    print(f"[DEBUG] Initializing taodian order dress task...")
    print(f"[DEBUG] Before orders: {len(self._before_orders)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_orders'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = taodian_validator.validate_order_created(
        env=env,
        before_orders=self._before_orders,
        expected={
            'prodId': self._PROD_ID,
            'skuId': self._SKUID,
            'prodCount': self._PROD_COUNT,
            'shopId': self._SHOPID,
            'contact_name': self._CONTACT_NAME,
            'phone': self._PHONE,
            'address': self._ADDRESS,
        },
        save_img_path=self.save_img_path,
        goal=self.full_goal,
    )
    return 1.0 if result else 0.0


class User7Long_SMSSendQuoteToContact(fixed_task_eval.TaskEval):
  """固定任务：给 Barbara Jones 发送 Joplin 中记录的名言。

  Agent 需要先在 Joplin 中找到记录的名言，然后通过 Simple SMS Messenger
  发送给 Barbara Jones。
  验证方式：检查短信数据库中是否有发送给目标号码的短信，且内容匹配。
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  _CONTACT_NAME = "Barbara Jones"
  _PHONE_NUMBER = "5555681480"
  _MESSAGE_BODY = "Life is like tea; it won't be bitter forever, but it will be bitter for a while. I think it's a great quote"
  _SNAPSHOT_NAME = "snapshot_7_long"

  @property
  def goal(self) -> str:
    return f"Share the quote I recorded with {self._CONTACT_NAME} via {self.app_name} app, tell her I think it's a great quote."

  @property
  def full_goal(self) -> str:
    return f"Send a text message to {self._CONTACT_NAME} via {self.app_name} app, saying '{self._MESSAGE_BODY}.'"

  @property
  def information(self):
    return "I recorded a quote in Joplin app that I think is great."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing SMS send quote task...")
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


class User7Long_OpenSolitairecg(fixed_task_eval.TaskEval):
  """固定任务：打开 solitairecg 游戏。

  Agent 需要打开 solitairecg 应用。
  验证方式：检查当前前台应用是否为 solitairecg。
  """

  app_name = "solitairecg"

  complexity = 4.0

  _TARGET_APP = "solitairecg"
  _SNAPSHOT_NAME = "snapshot_7_long"

  @property
  def goal(self) -> str:
    return "Open the card game I've been playing a lot today."

  @property
  def full_goal(self) -> str:
    return f"Open the {self._TARGET_APP} app."

  @property
  def information(self):
    return "It's a card game."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing open solitairecg task...")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = app_opened_validator.validate_app_opened(
        env=env,
        expected_app=self._TARGET_APP,
    )
    return 1.0 if result else 0.0


class User7Long_JingdianOrderCola(fixed_task_eval.TaskEval):
  """固定任务：在京店下单两箱罐装无糖可乐。

  Agent 需要在京店应用中下单两箱罐装无糖可乐。
  验证方式：比较操作前后的订单，检查是否有匹配的新订单。
  """

  app_name = "jingdian"

  complexity = 4.0

  _PRODID = '102'
  _SKUID = '102002'
  _SHOPID = '1'
  _PROD_COUNT = 2
  _SNAPSHOT_NAME = "snapshot_7_long"

  @property
  def goal(self) -> str:
    return f"The 'Zhou nian qing' celebration is coming up, order a few boxes of canned sugar-free cola on {self.app_name} app. Payment password is 123456"

  @property
  def full_goal(self) -> str:
    return f"Order two boxes of canned sugar-free cola on {self.app_name} app. Payment password is 123456"

  @property
  def information(self):
    return "The anniversary celebration event and number of attendees are recorded in simple calendar app."

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


class User7Long_TasksCreateShoppingList(fixed_task_eval.TaskEval):
  """固定任务：添加采购食材的待办。

  Agent 需要在 Tasks 应用中添加一个采购食材的待办，
  描述中记录 Braised spare ribs 所需的食材。
  验证方式：比较操作前后的任务列表，检查是否有匹配的新任务。
  """

  app_name = "tasks"

  complexity = 4.0

  _TASK_TITLE = "Buy ingredients"
  _TASK_NOTES = """Main ingredient: 500g pork ribs, choose lean pork ribs with less bones and more meat for better taste.
Seasoning: rock sugar, light soy sauce, dark soy sauce, cooking wine, scallions, ginger, garlic, star anise, cinnamon, fragrant leaves"""
  _SNAPSHOT_NAME = "snapshot_7_long"

  @property
  def goal(self) -> str:
    return f"Add a todo in {self.app_name} app for buying ingredients, with notes about the ingredients I need for Braised spare ribs. Due date is today."

  @property
  def full_goal(self) -> str:
    return f"Add a todo in {self.app_name} app with title '{self._TASK_TITLE}' and notes: {self._TASK_NOTES}. Due date is today."

  @property
  def information(self):
    return "I have a recipe for Braised spare ribs in the Broccoli app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_tasks = task_validator.get_tasks(env)
    print(f"[DEBUG] Initializing tasks create shopping list task...")
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


class User7Long_SMSSendFoodDelivery(fixed_task_eval.TaskEval):
  """固定任务：给 Mary Brown 发短信询问外卖是否收到。

  Agent 需要通过 Simple SMS Messenger 给 Mary Brown 发送短信，
  内容是询问她是否收到了外卖。
  验证方式：检查短信数据库中是否有发送给目标号码的短信，且内容匹配。
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  _CONTACT_NAME = "Mary Brown"
  _PHONE_NUMBER = "5556136850"
  _MESSAGE_BODY = "I ordered food delivery for you, have you received it?"
  _SNAPSHOT_NAME = "snapshot_7_long"

  @property
  def goal(self) -> str:
    return f"Send a text message to my friend via {self.app_name} app, telling her I ordered food delivery for her and asking if she has received it."

  @property
  def full_goal(self) -> str:
    return f"Send a text message to {self._CONTACT_NAME} via {self.app_name} app, saying '{self._MESSAGE_BODY}'"

  @property
  def information(self):
    return "I recommended a burger to a friend and then ordered food delivery for her."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing SMS send food delivery task...")
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
