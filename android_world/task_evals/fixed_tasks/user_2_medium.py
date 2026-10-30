

"""固定任务：中等任务集合。

包含以下任务：
- ExpenseAddOther: 在Pro Expense中记录一笔其他类型的消费
- RetroMusicAddToPlaylist: 在Retro Music中将歌曲添加到播放列表
- ChilemeiOrderFood: 在Chilemei上下单外卖
- ChilemeiOrderFruit: 在Chilemei上订购水果
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import chilemei as chilemei_validator
from android_world.task_evals.custom_validators import expense as expense_validator
from android_world.task_evals.custom_validators import retro_music as retro_music_validator


class User2Medium_ExpenseAddOther(fixed_task_eval.TaskEval):
  """固定任务：在Pro Expense中记录一笔其他类型的消费。

  Agent 需要在 Pro Expense 应用中记录一笔 180.57 元的消费，类型选择其他。
  验证方式：比较任务执行前后的记账数据库，检查新增记录是否匹配。
  """

  app_name = "pro expense"

  complexity = 4.0

  _EXPENSE_NAME = "technology"
  _EXPENSE_AMOUNT = 18057  # 180.57元，单位：分
  _ALT_EXPENSE_AMOUNT = 18067  # 180.67元，单位：分（均可接受）
  _CATEGORY = "Others"
  _SNAPSHOT_NAME = "snapshot_2_medium"

  @property
  def goal(self) -> str:
    return f"Record the total amount from the receipt I calculated in the {self.app_name} app, name it technology, and set the category to Others."

  @property
  def full_goal(self) -> str:
    return f"Record an expense of 180.57 yuan named technology with the category set to Others in the {self.app_name} app."

  @property
  def information(self):
    return "I just calculated the total amount of that receipt using the calculator."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_expenses = expense_validator.get_expenses(env)
    print(f"[DEBUG] Initializing expense add other task...")
    print(f"[DEBUG] Before expenses: {len(self._before_expenses)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_expenses'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    for amount in (self._EXPENSE_AMOUNT, self._ALT_EXPENSE_AMOUNT):
      result = expense_validator.validate_expense_added(
          env=env,
          goal=self.full_goal,
          before_expenses=self._before_expenses,
          expected_name=self._EXPENSE_NAME,
          expected_amount=amount,
          expected_category=self._CATEGORY,
      )
      if result:
        return 1.0

    return 0.0


class User2Medium_RetroMusicAddToPlaylist(fixed_task_eval.TaskEval):
  """固定任务：在Retro Music中将两首歌曲添加到播放列表。

  Agent 需要在 Retro Music 中将 Forever Young 和 Moments 两首歌加到播放列表。
  验证方式：检查是否存在一个仅包含这两首歌曲的播放列表。
  """

  app_name = "retro music"

  complexity = 4.0

  _SONGS = ["Forever Young", "Moments"]
  _SNAPSHOT_NAME = "snapshot_2_medium"

  @property
  def goal(self) -> str:
    return f"Please add the two recommended songs to a playlist in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Add the songs Forever Young and Moments to a playlist in {self.app_name} app."

  @property
  def information(self):
    return "Mary Jones recommended two songs to me via simple sms messenger."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing retro music add to playlist task...")
    print(f"[DEBUG] Expected songs: {self._SONGS}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    playlists = retro_music_validator.get_playlist_data(env)
    print(f"[DEBUG] Found {len(playlists)} playlist entries")

    # Group songs by playlist name
    playlist_songs = {}
    for entry in playlists:
      name = entry.playlist_name
      if name not in playlist_songs:
        playlist_songs[name] = []
      playlist_songs[name].append(entry.media_file_name.lower().strip())

    expected = [s.lower().strip() for s in self._SONGS]

    for name, songs in playlist_songs.items():
      if songs == expected:
        print(f"[DEBUG] Found matching playlist '{name}' with songs: {songs}")
        return 1.0

    print(f"[DEBUG] No playlist found with exactly these songs: {expected}")
    print(f"[DEBUG] Existing playlists: {playlist_songs}")
    return 0.0


class User2Medium_ChilemeiOrderFood(fixed_task_eval.TaskEval):
  """固定任务：在Chilemei上指定餐馆下单指定食物。

  Agent 需要在 Chilemei 的好味道中餐馆下单一份牛肉面。
  验证方式：比较任务执行前后的订单数据，检查新订单是否匹配。
  """

  app_name = "chilemei"

  complexity = 4.0

  _SHOP_NAME = "好味道中餐馆"
  _FOOD_NAME = "牛肉面(大份)"
  _SNAPSHOT_NAME = "snapshot_2_medium"

  @property
  def goal(self) -> str:
    return f"I want to eat the same noodles as in the picture I saw earlier, please order one from {self._SHOP_NAME} on {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Order one {self._FOOD_NAME} from {self._SHOP_NAME} on {self.app_name} app."

  @property
  def information(self):
    return "I looked at a picture of beef noodles in simple gallery app earlier."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_orders = chilemei_validator.get_orders(env)
    print(f"[DEBUG] Initializing chilemei order food task...")
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
        },
    )
    return 1.0 if result else 0.0


class User2Medium_ChilemeiOrderFruit(fixed_task_eval.TaskEval):
  """固定任务：在Chilemei上订购水果。

  Agent 需要在 Chilemei 的绿色水果店下单10份车厘子。
  验证方式：比较任务执行前后的订单数据，检查新订单是否匹配。
  """

  app_name = "chilemei"

  complexity = 4.0

  _SHOP_NAME = "绿色水果店"
  _FOOD_NAME = "草莓"
  _NUM = 10
  _SNAPSHOT_NAME = "snapshot_2_medium"

  @property
  def goal(self) -> str:
    return f"Please buy some fruit on {self.app_name} app. Buy as many portions as the number of people attending the meeting."

  @property
  def full_goal(self) -> str:
    return f"Order {self._NUM} portions of {self._FOOD_NAME} from {self._SHOP_NAME} on {self.app_name} app."

  @property
  def information(self):
    return "Mary Brown sent me a text message about the meeting tomorrow via simple sms messenger, which mentioned how many people are attending."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_orders = chilemei_validator.get_orders(env)
    print(f"[DEBUG] Initializing chilemei order fruit task...")
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
        },
    )
    return 1.0 if result else 0.0