

"""固定任务：中等任务集合。

包含以下任务：
- ChilemeiOrderNoodles: 在吃了没中下单一份经典肉酱面
- TasksCreateTodo: 在 Tasks 中创建 trail run 待办
- TaodianOrderTShirt: 在淘店下单一件运动型透气T恤
- RetroMusicPlaySong: 在 Retro Music 中播放 Bright Lights
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import chilemei as chilemei_validator
from android_world.task_evals.custom_validators import retro_music as retro_music_validator
from android_world.task_evals.custom_validators import task as task_validator
from android_world.task_evals.custom_validators import taodian as taodian_validator


class User4Medium_ChilemeiOrderNoodles(fixed_task_eval.TaskEval):
  """固定任务：在吃了没中下单一份经典肉酱面。

  Agent 需要在 Chilemei 的意识手工面坊下单一份经典肉酱面，
  地址设置为 Lijin Land Center, Weigongcun Road, Haidian District, Beijing。
  验证方式：比较任务执行前后的订单数据，检查新订单是否匹配。
  """

  app_name = "chilemei"

  complexity = 4.0

  _SHOP_NAME = "意式手工面坊"
  _FOOD_NAME = "经典肉酱面"
  _ADDRESS = "Lijin Land Center, Weigongcun Road, Haidian District, Beijing"
  _CONTACT_NAME = "Barbara Jones"
  _PHONE = "13344556677"
  _SNAPSHOT_NAME = "snapshot_4_medium"

  @property
  def goal(self) -> str:
    return f"Please order a {self._FOOD_NAME} from {self._SHOP_NAME} on {self.app_name} app for {self._CONTACT_NAME}, phone number {self._PHONE}, deliver to her place."

  @property
  def full_goal(self) -> str:
    return f"Order one {self._FOOD_NAME} from {self._SHOP_NAME} on {self.app_name} app for {self._CONTACT_NAME}, phone number {self._PHONE}, deliver to {self._ADDRESS}."

  @property
  def information(self):
    return "She sent me the delivery address via simple sms messenger."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_orders = chilemei_validator.get_orders(env)
    print(f"[DEBUG] Initializing chilemei order noodles task...")
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
            'num': 1,
            'address': self._ADDRESS,
            'phone': self._PHONE,
            'contact_name': self._CONTACT_NAME,
        },
        goal=self.full_goal,
    )
    return 1.0 if result else 0.0


class User4Medium_TasksCreateTodo(fixed_task_eval.TaskEval):
  """固定任务：在 Tasks 应用中创建待办。

  Agent 需要在 Tasks 应用中创建一个 trail run 待办，
  内容是关于跑完剩余的 4.42 mile。
  验证方式：使用 LLM 判断待办内容是否符合要求。
  """

  app_name = "tasks"

  complexity = 4.0

  _TASK_TITLE = "trail run"
  _TASK_NOTES = "4.42 miles left to run"
  _DUE_DATE = "2026-05-21"
  _DUE_DATE_TS = 1779364800000  # 2026-05-21
  _SNAPSHOT_NAME = "snapshot_4_medium"

  @property
  def goal(self) -> str:
    return f"I plan to run a total of 15 miles for trail run this month, ending on May 21. I've already run several miles so far. Please help me write a todo with the remaining miles to run in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Create a todo in tasks named '{self._TASK_TITLE}' with due date {self._DUE_DATE} and notes '{self._TASK_NOTES}' in {self.app_name} app."

  @property
  def information(self):
    return "OpenTracks app recorded how many miles I've already run for trail run."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_tasks = task_validator.get_tasks(env)
    print(f"[DEBUG] Initializing tasks create todo task...")
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


class User4Medium_TaodianOrderTShirt(fixed_task_eval.TaskEval):
  """固定任务：在淘店下单一件运动型透气T恤。

  Agent 需要在 Taodian 淘店中下单一件 S 码的运动型透气T恤。
  验证方式：比较任务执行前后的订单数据，检查新订单是否匹配。
  """

  app_name = "taodian"

  complexity = 4.0

  _PROD_NAME = "运动型透气T恤"
  _SKU_NAME = "S码"
  _PRODID = "2"
  _SKUID = "2001"
  _SHOPID = "1"
  _PROD_COUNT = 1
  _SNAPSHOT_NAME = "snapshot_4_medium"

  @property
  def goal(self) -> str:
    return f"In {self.app_name} app, help me buy the same black t-shirt I saw earlier, size S. The payment password is: 123456."

  @property
  def full_goal(self) -> str:
    return f"Order one {self._SKU_NAME} {self._PROD_NAME} from {self.app_name} app. The payment password is: 123456."

  @property
  def information(self):
    return "I looked at a black sporty breathable t-shirt in simple gallery app earlier."

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
            'prodCount': self._PROD_COUNT,
        },
    )
    return 1.0 if result else 0.0


class User4Medium_RetroMusicPlaySong(fixed_task_eval.TaskEval):
  """固定任务：在 Retro Music 中播放 Bright Lights。

  Agent 需要在 Retro Music 中播放 Bright Lights 这首歌。
  验证方式：检查当前播放的歌曲是否为 Bright Lights。
  """

  app_name = "retro music"

  complexity = 4.0

  _SONG_TITLE = "Bright Lights"
  _SNAPSHOT_NAME = "snapshot_4_medium"

  @property
  def goal(self) -> str:
    return f"The second song I played this morning was really nice, please play it for me in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Play {self._SONG_TITLE} in {self.app_name} app."

  @property
  def information(self):
    return "The second song I played in retro music this morning should be the second song in the songs list."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing retro music play song task...")
    print(f"[DEBUG] Expected song: {self._SONG_TITLE}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = retro_music_validator.validate_song_playing(
        env=env,
        expected_song_title=self._SONG_TITLE,
        fuzzy_match=True,
    )
    return 1.0 if result else 0.0
