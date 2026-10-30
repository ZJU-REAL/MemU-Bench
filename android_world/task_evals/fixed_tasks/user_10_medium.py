

"""固定任务：中等任务集合。

包含以下任务：
- JingdianOrderTShirt: 在 Jingdian 下单一件 S 码的经典白色 T 恤
- TasksAddPickupGifts: 添加一个待办，日期是明天，内容是拿朋友送的礼物
- ContactsAddJessicaGarcia2: 添加一个联系人 Jessica Garcia 2
- GalleryFavoriteReceipt: 收藏 receipt_001.jpg 图片
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import contacts as contacts_validator
from android_world.task_evals.custom_validators import files as files_validator
from android_world.task_evals.custom_validators import jingdian as jingdian_validator
from android_world.task_evals.custom_validators import task as task_validator


class User10Medium_JingdianOrderTShirt(fixed_task_eval.TaskEval):
  """固定任务：在 Jingdian 下单一件 S 码的经典白色 T 恤。

  Agent 需要在 Jingdian 应用中购买一件 S 码的经典白色 T 恤，
  收件人姓名 William Smith，电话号码 12344445566，
  地址为 Room 505, 5th Floor, Beixintong Building, Beiyuan Road, Chaoyang District, Beijing。
  验证方式：比较操作前后的订单，检查是否有匹配的新订单。
  """

  app_name = "jingdian"

  complexity = 4.0

  _PROD_NAME = "经典白色 T 恤"
  _SKU_NAME = "S 码"
  _PRODID = '1'
  _SKUID = '1001'
  _SHOPID = '1'
  _PROD_COUNT = 1
  _CONTACT_NAME = "William Smith"
  _PHONE = "12344445566"
  _ADDRESS = "Room 505, 5th Floor, Beixintong Building, Beiyuan Road, Chaoyang District, Beijing"
  _SNAPSHOT_NAME = "snapshot_10_medium"

  @property
  def goal(self) -> str:
    return f"Order a {self._SKU_NAME} {self._PROD_NAME} on {self.app_name} app, with contact name {self._CONTACT_NAME}, phone number {self._PHONE}, and fill in his new home address. Payment password is 123456"

  @property
  def full_goal(self) -> str:
    return f"Order a {self._SKU_NAME} {self._PROD_NAME} on {self.app_name} app, contact name is {self._CONTACT_NAME}, phone number is {self._PHONE}, address is {self._ADDRESS}. Payment password is 123456"

  @property
  def information(self):
    return f"{self._CONTACT_NAME} texted me his new address via simple sms messenger app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_orders = jingdian_validator.get_orders(env)
    print(f"[DEBUG] Initializing jingdian order t-shirt task...")
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
            'contact_name': self._CONTACT_NAME,
            'phone': self._PHONE,
            'address': self._ADDRESS,
        },
        save_img_path=self.save_img_path,
        goal=self.full_goal,
    )
    return 1.0 if result else 0.0


class User10Medium_TasksAddPickupGifts(fixed_task_eval.TaskEval):
  """固定任务：添加一个待办，明天去拿朋友送的礼物。

  Agent 需要在 Tasks 应用中添加一个待办事项，
  截止日期设为明天，
  内容是去拿 David Johnson 和 Barbara Jones 送的礼物。
  验证方式：比较操作前后的任务列表，检查是否有匹配的新任务。
  """

  app_name = "tasks"

  complexity = 4.0

  _TASK_TITLE = "Pick up gifts from David Johnson and Barbara Jones"
  _DUE_DATE = 1778673600000  # 2026-05-13 00:00:00 UTC (tomorrow)
  _SNAPSHOT_NAME = "snapshot_10_medium"

  @property
  def goal(self) -> str:
    return f"Add a todo in {self.app_name} app for tomorrow, about picking up gifts from several friends."

  @property
  def full_goal(self) -> str:
    return f"Add a todo '{self._TASK_TITLE}' in {self.app_name} app with due date tomorrow."

  @property
  def information(self):
    return "David Johnson and Barbara Jones texted me that they have gifts for me via simple sms messenger app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_tasks = task_validator.get_tasks(env)
    print(f"[DEBUG] Initializing tasks add pickup gifts task...")
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
        expected_due_date=self._DUE_DATE,
    )
    return 1.0 if result else 0.0


class User10Medium_ContactsAddJessicaGarcia2(fixed_task_eval.TaskEval):
  """固定任务：添加联系人 Jessica Garcia 2。

  Agent 需要在 Contacts 应用中添加一个联系人，
  电话号码为 5551078962。
  验证方式：比较操作前后的联系人列表，检查是否有匹配的新联系人。
  """

  app_name = "contacts"

  complexity = 4.0

  _CONTACT_NAME = "Professor 2"
  _PHONE_NUMBER = "5551078962"
  _SNAPSHOT_NAME = "snapshot_10_medium"

  @property
  def goal(self) -> str:
    return f"Add the professor's alternate phone number to contacts. Contact Name is {self._CONTACT_NAME}."

  @property
  def full_goal(self) -> str:
    return f"Add a contact in {self.app_name} app with name '{self._CONTACT_NAME}' and phone number '{self._PHONE_NUMBER}'."

  @property
  def information(self):
    return "Jessica Garcia texted me her alternate phone number via simple sms messenger app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_contacts = contacts_validator.get_contacts(env)
    print(f"[DEBUG] Initializing contacts add Jessica Garcia 2 task...")
    print(f"[DEBUG] Before contacts: {len(self._before_contacts)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_contacts'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = contacts_validator.validate_contact_added(
        env=env,
        before_contacts=self._before_contacts,
        expected_name=self._CONTACT_NAME,
        expected_number=self._PHONE_NUMBER,
    )
    return 1.0 if result else 0.0


class User10Medium_GalleryFavoriteReceipt(fixed_task_eval.TaskEval):
  """固定任务：在 Simple Gallery 中收藏 receipt_001.jpg 图片。

  Agent 需要在 Simple Gallery Pro 应用中收藏 receipt_001.jpg 图片。
  验证方式：检查图片是否被标记为收藏。
  """

  app_name = "simple gallery pro"

  complexity = 4.0

  _FILE_NAME = "receipt_001.jpg"
  _FILE_DIRECTORY = "/sdcard/DCIM"
  _SNAPSHOT_NAME = "snapshot_10_medium"

  def __init__(self):
    super().__init__()
    self._before_favorites = None

  @property
  def goal(self) -> str:
    return f"Favorite the receipt image that I viewed many times in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Favorite the {self._FILE_NAME} image in {self.app_name} app."

  @property
  def information(self):
    return "The receipt contains a bluetooth keyboard costing around 35 yuan."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_favorites = files_validator.get_favorites(env)
    print(f"[DEBUG] Initializing gallery favorite receipt task...")
    print(f"[DEBUG] Target: {self._FILE_NAME} in {self._FILE_DIRECTORY}")
    print(f"[DEBUG] Before favorites: {len(self._before_favorites)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = files_validator.validate_image_favorited(
        env=env,
        file_name=self._FILE_NAME,
        directory_path=self._FILE_DIRECTORY,
        before_favorites=self._before_favorites,
    )
    return 1.0 if result else 0.0