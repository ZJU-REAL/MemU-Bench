

"""固定任务：长任务集合。

包含以下任务：
- TuantuanOrderKungPaoChicken: 在好味道中餐馆下单宫保鸡丁
- ChilemeiOrderSpicyChicken: 在吃了没下单麻辣鸡块
- JoplinCreateNoteClothes: 创建笔记记录黑色经典T恤
- JoplinCreateNoteThreeBody: 创建笔记记录三体阅读进度
- GalleryDeleteDress: 删除相册中的裙子图片
- ExpenseRecordTravel: 记录一笔旅游消费
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import chilemei as chilemei_validator
from android_world.task_evals.custom_validators import expense as expense_validator
from android_world.task_evals.custom_validators import files as files_validator
from android_world.task_evals.custom_validators import joplin as joplin_validator
from android_world.task_evals.custom_validators import tuantuan as tuantuan_validator


class User4Long_TuantuanOrderKungPaoChicken(fixed_task_eval.TaskEval):
  """固定任务：在好味道中餐馆下单宫保鸡丁。

  Agent 需要在 Tuantuan 淘团购中下单一份宫保鸡丁，
  送到 Lijin Land Center in Weigongcun，联系人是 Me，电话是 13312345678。
  验证方式：比较任务执行前后的订单数据，检查新订单是否匹配。
  """

  app_name = "tuantuanwaimai"

  complexity = 4.0

  _SHOP_NAME = "好味道中餐馆"
  _FOOD_NAME = "宫保鸡丁"
  _ADDRESS = "Lijin Land Center in Weigongcun"
  _CONTACT_NAME = "Me"
  _PHONE = "13312345678"
  _SNAPSHOT_NAME = "snapshot_4_long"

  @property
  def goal(self) -> str:
    return f"Order {self._FOOD_NAME} from {self._SHOP_NAME} on {self.app_name} app, deliver to my company, contact name is {self._CONTACT_NAME}, phone number is {self._PHONE}."

  @property
  def full_goal(self) -> str:
    return f"Order one {self._FOOD_NAME} from {self._SHOP_NAME} on {self.app_name} app, deliver to {self._ADDRESS}, contact name is {self._CONTACT_NAME}, phone number is {self._PHONE}."

  @property
  def information(self):
    return "I told David Johnson my current company address via simple sms messenger app, please find it there."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_orders = tuantuan_validator.get_orders(env)
    print(f"[DEBUG] Initializing tuantuan order kung pao chicken task...")
    print(f"[DEBUG] Before orders: {len(self._before_orders)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_orders'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = tuantuan_validator.validate_order_created(
        env=env,
        before_orders=self._before_orders,
        expected={
            'shop_name': self._SHOP_NAME,
            'food_name': self._FOOD_NAME,
            'num': 1,
            'address': self._ADDRESS,
            'phone': self._PHONE,
            'contact_name': self._CONTACT_NAME,
        },
        goal=self.full_goal,
    )
    return 1.0 if result else 0.0


class User4Long_ChilemeiOrderSpicyChicken(fixed_task_eval.TaskEval):
  """固定任务：在大大炸鸡店铺下单麻辣鸡块。

  Agent 需要在 Chilemei 吃了没中下单4份麻辣鸡块，
  送到 Lijin Land Center in Weigongcun，联系人是 Me，电话是 13312345678。
  验证方式：比较任务执行前后的订单数据，检查新订单是否匹配。
  """

  app_name = "chilemei"

  complexity = 4.0

  _SHOP_NAME = "大大炸鸡"
  _FOOD_NAME = "麻辣鸡块"
  _NUM = 4
  _ADDRESS = "北京市朝阳区"
  _CONTACT_NAME = "张三"
  _PHONE = "13812345678"
  _SNAPSHOT_NAME = "snapshot_4_long"

  @property
  def goal(self) -> str:
    return f"Order some portions of {self._FOOD_NAME} from {self._SHOP_NAME} on {self.app_name} app, deliver to my company, contact name is {self._CONTACT_NAME}, phone number is {self._PHONE}. The number of portions should be the number of people who attended the meeting on May 8th divided by 2."

  @property
  def full_goal(self) -> str:
    return f"Order {self._NUM} portions of {self._FOOD_NAME} from {self._SHOP_NAME} on {self.app_name} app, deliver to {self._ADDRESS}, contact name is {self._CONTACT_NAME}, phone number is {self._PHONE}."

  @property
  def information(self):
    return "I have a meeting on May 8th recorded in simple calendar app, which shows the number of attendees. Also, Mary Brown texted me via simple sms messenger app to tell me who won't be attending the meeting."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_orders = chilemei_validator.get_orders(env)
    print(f"[DEBUG] Initializing chilemei order spicy chicken task...")
    print(f"[DEBUG] Before orders: {len(self._before_orders)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_orders'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = chilemei_validator.validate_order_created(
        env=env,
        before_orders=self._before_orders,
        expected={
            'shop_name': self._SHOP_NAME,
            'food_name': self._FOOD_NAME,
            'num': self._NUM,
            'address': self._ADDRESS,
            'phone': self._PHONE,
            'contact_name': self._CONTACT_NAME,
        },
        goal=self.full_goal,
    )
    return 1.0 if result else 0.0


class User4Long_JoplinCreateNoteClothes(fixed_task_eval.TaskEval):
  """固定任务：在 Joplin 中创建笔记记录衣服信息。

  Agent 需要在 Joplin 中创建一个笔记，
  标题是衣服，内容是款式：黑色基础t-shirt，金额是79元。
  验证方式：比较任务执行前后的笔记数据，检查新笔记是否匹配。
  """

  app_name = "joplin"

  complexity = 4.0

  _NOTE_TITLE = "Clothes"
  _NOTE_BODY = "Style: black classic t-shirt, Price: 79 yuan"
  _SNAPSHOT_NAME = "snapshot_4_long"

  @property
  def goal(self) -> str:
    return f"Create a note in {self.app_name} app about the black classic t-shirt I viewed earlier, include the style and price."

  @property
  def full_goal(self) -> str:
    return f"Create a note in {self.app_name} app with title '{self._NOTE_TITLE}' and body '{self._NOTE_BODY}'."

  @property
  def information(self):
    return "I viewed a black classic t-shirt on taodian app earlier."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_notes = joplin_validator.get_notes(env)
    print(f"[DEBUG] Initializing joplin create note clothes task...")
    print(f"[DEBUG] Before notes: {len(self._before_notes)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_notes'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = joplin_validator.validate_note_added(
        env=env,
        goal=self.full_goal,
        before_notes=self._before_notes,
        expected_title=self._NOTE_TITLE,
        expected_body=self._NOTE_BODY,
    )
    return 1.0 if result else 0.0


class User4Long_JoplinCreateNoteThreeBody(fixed_task_eval.TaskEval):
  """固定任务：在 Joplin 中创建笔记记录三体阅读进度。

  Agent 需要在 Joplin 中创建一个笔记，
  标题是三体，内容是看到12页了。
  验证方式：比较任务执行前后的笔记数据，检查新笔记是否匹配。
  """

  app_name = "joplin"

  complexity = 4.0

  _NOTE_TITLE = "Reading 三体"
  _NOTE_BODY = "Currently on page 12"
  _SNAPSHOT_NAME = "snapshot_4_long"

  @property
  def goal(self) -> str:
    return f"Create a note in {self.app_name} app about how many pages I've read in the book 三体."

  @property
  def full_goal(self) -> str:
    return f"Create a note in {self.app_name} app with title '{self._NOTE_TITLE}' and body '{self._NOTE_BODY}'."

  @property
  def information(self):
    return "I opened and read the book 三体 in librera fd app earlier."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_notes = joplin_validator.get_notes(env)
    print(f"[DEBUG] Initializing joplin create note three body task...")
    print(f"[DEBUG] Before notes: {len(self._before_notes)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_notes'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = joplin_validator.validate_note_added(
        env=env,
        goal=self.full_goal,
        before_notes=self._before_notes,
        expected_title=self._NOTE_TITLE,
        expected_body=self._NOTE_BODY,
    )
    return 1.0 if result else 0.0


class User4Long_GalleryDeleteDress(fixed_task_eval.TaskEval):
  """固定任务：在 Simple Gallery 中删除裙子图片。

  Agent 需要在 Simple Gallery Pro 中删除 2.png 图片。
  验证方式：检查文件系统中该图片是否已被删除。
  """

  app_name = "simple gallery"

  complexity = 4.0

  _FILE_NAME = "2.png"
  _FILE_DIRECTORY = "/sdcard/DCIM"
  _SNAPSHOT_NAME = "snapshot_4_long"

  def __init__(self):
    super().__init__()
    self._initial_files = None

  @property
  def goal(self) -> str:
    return f"Delete the dress picture I viewed multiple times earlier from {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Delete the file named {self._FILE_NAME} from {self.app_name} app."

  @property
  def information(self):
    return "I viewed a ladies lace floral cocktail dress picture multiple times in simple gallery app earlier."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._initial_files = [
        f.name for f in files_validator.get_files_in_directory(
            env, self._FILE_DIRECTORY
        )
    ]
    print(f"[DEBUG] Initializing gallery delete dress task...")
    print(f"[DEBUG] Target file: {self._FILE_NAME} in {self._FILE_DIRECTORY}")
    print(f"[DEBUG] Initial files in directory: {self._initial_files}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if self._initial_files is None:
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = files_validator.validate_file_deleted(
        env=env,
        file_name=self._FILE_NAME,
        directory_path=self._FILE_DIRECTORY,
        initial_files=self._initial_files,
    )
    return 1.0 if result else 0.0


class User4Long_ExpenseRecordTravel(fixed_task_eval.TaskEval):
  """固定任务：在 Pro Expense 中记录旅游消费。

  Agent 需要在 Pro Expense 应用中记录一笔消费，
  名字是旅游，金额是 1035 元，类别是 social。
  验证方式：使用 LLM 判断记账记录是否符合要求。
  """

  app_name = "pro expense"

  complexity = 4.0

  _EXPENSE_NAME = "Travel"
  _EXPENSE_AMOUNT = 103500  # 1035元，单位：分
  _CATEGORY = "Social"
  _SNAPSHOT_NAME = "snapshot_4_long"

  @property
  def goal(self) -> str:
    return f"Record my travel expense in {self.app_name} app, name it 'Travel', category is 'social', the amount is around 1000 yuan which I calculated earlier using the calculator."

  @property
  def full_goal(self) -> str:
    return f"Record an expense in {self.app_name} app named '{self._EXPENSE_NAME}' with amount 1035 yuan and category '{self._CATEGORY}'."

  @property
  def information(self):
    return "The exact amount is 1035 yuan."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_expenses = expense_validator.get_expenses(env)
    print(f"[DEBUG] Initializing expense record travel task...")
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