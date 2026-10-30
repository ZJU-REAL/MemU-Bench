

"""固定任务：长任务集合。

包含以下任务：
- CalendarModifyInfoSecTraining: 修改 information security training session 的时间
- BroccoliDeletePanSearedSalmon: 删除 Pan-Seared Salmon with Quinoa 食谱
- BroccoliModifySpicyTunaWraps: 修改 Spicy Tuna Wraps 食谱的 Directions
- JoplinAddReimbursementNote: 在 Joplin 中添加报销笔记
- CalendarAddFieldTrip: 添加 Field trip to Alibaba 日程
- TaodianOrderMouse: 在淘店购买罗技 G102 游戏鼠标
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import calendar as calendar_validator
from android_world.task_evals.custom_validators import clock as clock_validator
from android_world.task_evals.custom_validators import joplin as joplin_validator
from android_world.task_evals.custom_validators import recipe as recipe_validator
from android_world.task_evals.custom_validators import taodian as taodian_validator


class User9Long_CalendarAddFieldTrip(fixed_task_eval.TaskEval):
  """固定任务：添加 Field trip to Alibaba 日程。

  Agent 需要在 Simple Calendar Pro 中添加一个日程，
  标题是 Field trip to Alibaba，时间是 5 月 20 日下午 2 点。
  验证方式：比较任务执行前后的日程数据，检查新日程是否匹配。
  """

  app_name = "simple calendar"

  complexity = 4.0

  _EVENT_TITLE = "Field trip to Alibaba"
  _EVENT_DATE = "2026-05-20"
  _EVENT_START_TS = 1779285600  # 2026-05-20 14:00:00 UTC
  _SNAPSHOT_NAME = "snapshot_9_long"

  @property
  def goal(self) -> str:
    return f"Add next Wednesday's event to {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Add a calendar event in {self.app_name} app with title '{self._EVENT_TITLE}' at 2:00 PM on {self._EVENT_DATE}."

  @property
  def information(self):
    return "I recorded an event next Wednesday in Joplin."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_events = calendar_validator.get_current_events(env)
    print(f"[DEBUG] Initializing calendar add field trip task...")
    print(f"[DEBUG] Before events: {len(self._before_events)}")

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
    )
    return 1.0 if result else 0.0


class User9Long_CalendarModifyInfoSecTraining(fixed_task_eval.TaskEval):
  """固定任务：修改 information security training session 的时间。

  Agent 需要将日历中 5 月 15 日的 information security training session
  的时间修改为 14:30，同时将下午 2 点的闹钟修改为 14:30。
  验证方式：检查日历事件的时间是否被正确修改，同时检查闹钟时间是否同步修改。
  """

  app_name = "simple calendar"

  complexity = 4.0

  _EVENT_TITLE = "information security training session"
  _EVENT_DATE = "2026-05-15"
  _NEW_START_TS = 1778855400  # 2026-05-15 14:30:00 UTC
  _ALARM_OLD_HOUR = 14
  _ALARM_OLD_MINUTE = 0
  _ALARM_NEW_HOUR = 14
  _ALARM_NEW_MINUTE = 30
  _SNAPSHOT_NAME = "snapshot_9_long"

  @property
  def goal(self) -> str:
    return f"Change the calendar session time in {self.app_name} app, and then update the alarm time accordingly."

  @property
  def full_goal(self) -> str:
    return f"Modify the {self._EVENT_TITLE} event on {self._EVENT_DATE} to start at 14:30 in {self.app_name} app, and then change the 2:00 PM alarm to 2:30 PM."

  @property
  def information(self):
    return "Charles Martinez texted me via simple sms messenger app that the session is postponed."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_events = calendar_validator.get_current_events(env)
    print(f"[DEBUG] Initializing calendar modify info sec training task...")
    print(f"[DEBUG] Before events: {len(self._before_events)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_events'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    # 验证日历事件时间是否被修改
    calendar_result = calendar_validator.validate_event_time_modified(
        env=env,
        before_events=self._before_events,
        expected_title=self._EVENT_TITLE,
        expected_start_ts=self._NEW_START_TS,
    )

    if not calendar_result:
      print("[DEBUG] Calendar event time modification failed")
      return 0.0

    # 验证闹钟时间是否被修改
    alarm_result = clock_validator.validate_alarm_time_changed(
        env=env,
        old_hour=self._ALARM_OLD_HOUR,
        old_minute=self._ALARM_OLD_MINUTE,
        new_hour=self._ALARM_NEW_HOUR,
        new_minute=self._ALARM_NEW_MINUTE,
    )

    if not alarm_result:
      print("[DEBUG] Alarm time modification failed")
      return 0.0

    print("[DEBUG] Both calendar event and alarm time modifications validated successfully")
    return 1.0


class User9Long_BroccoliDeletePanSearedSalmon(fixed_task_eval.TaskEval):
  """固定任务：删除 Pan-Seared Salmon with Quinoa 食谱。

  Agent 需要在 Broccoli 食谱应用中删除 Pan-Seared Salmon with Quinoa 食谱。
  验证方式：检查食谱是否被正确删除。
  """

  app_name = "broccoli"

  complexity = 4.0

  _RECIPE_TITLE = "Pan-Seared Salmon with Quinoa"
  _SNAPSHOT_NAME = "snapshot_9_long"

  @property
  def goal(self) -> str:
    return f"Delete the recipe I opened before playing solitairecg in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Delete the {self._RECIPE_TITLE} recipe (servings: 2) in {self.app_name} app."

  @property
  def information(self):
    return "The recipe I opened before playing solitairecg has Pan-Seared in its name."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_recipes = recipe_validator.get_recipes(env)
    print(f"[DEBUG] Initializing broccoli delete pan seared salmon task...")
    print(f"[DEBUG] Before recipes: {len(self._before_recipes)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_recipes'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = recipe_validator.validate_recipe_deleted(
        env=env,
        before_recipes=self._before_recipes,
        expected={'title': self._RECIPE_TITLE},
    )
    return 1.0 if result else 0.0


class User9Long_BroccoliModifySpicyTunaWraps(fixed_task_eval.TaskEval):
  """固定任务：修改 Spicy Tuna Wraps 食谱的 Directions。

  Agent 需要在 Broccoli 食谱应用中修改 Spicy Tuna Wraps 食谱的 Directions。
  验证方式：使用 LLM 判断 Directions 是否被正确修改。
  """

  app_name = "broccoli"

  complexity = 4.0

  _RECIPE_TITLE = "Spicy Tuna Wraps"
  _NEW_DIRECTIONS = ("Drain the tuna, then mix in Korean chili paste and a little mayonnaise to create a spicy filling; "
                     "Spread the rice evenly over the nori, press it down firmly, then layer the vegetable strips, tuna filling, and pork floss in that order; "
                     "Roll it up tightly from one end, then cut it into small pieces")
  _SNAPSHOT_NAME = "snapshot_9_long"

  @property
  def goal(self) -> str:
    return f"A friend recommended a new way to make a recipe, help me modify the Directions of that recipe in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Modify the {self._RECIPE_TITLE} recipe's Directions to '{self._NEW_DIRECTIONS}' in {self.app_name} app."

  @property
  def information(self):
    return "William Jones texted me via simple sms messenger app to recommend a new way to make Spicy Tuna Wraps."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_recipes = recipe_validator.get_recipes(env)
    print(f"[DEBUG] Initializing broccoli modify spicy tuna wraps task...")
    print(f"[DEBUG] Before recipes count: {len(self._before_recipes)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_recipes'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = recipe_validator.validate_recipe_modified(
        env=env,
        before_recipes=self._before_recipes,
        expected_title=self._RECIPE_TITLE,
        expected_field='directions',
        expected_value=self._NEW_DIRECTIONS,
    )
    return 1.0 if result else 0.0


class User9Long_JoplinAddReimbursementNote(fixed_task_eval.TaskEval):
  """固定任务：在 Joplin 中添加报销笔记。

  Agent 需要在 Joplin 中创建一个笔记，
  标题是报销，内容是需要报销 68.02 元。
  验证方式：比较任务执行前后的笔记数据，检查新笔记是否匹配。
  """

  app_name = "joplin"

  complexity = 4.0

  _NOTE_TITLE = "Reimbursement"
  _NOTE_BODY = "Need to reimburse 68.02 yuan"
  _SNAPSHOT_NAME = "snapshot_9_long"

  @property
  def goal(self) -> str:
    return f"I calculated the reimbursement amount, help me create a note in {self.app_name} app with the reimbursement details."

  @property
  def full_goal(self) -> str:
    return f"Create a note in {self.app_name} app with title 'Reimbursement' and body 'Need to reimburse 68.02 yuan'."

  @property
  def information(self):
    return "I calculated the reimbursement amount in calculator app, it was nearly 70 yuan."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_notes = joplin_validator.get_notes(env)
    print(f"[DEBUG] Initializing joplin add reimbursement note task...")
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


class User9Long_TaodianOrderMouse(fixed_task_eval.TaskEval):
  """固定任务：在淘店购买罗技 G102 游戏鼠标。

  Agent 需要在 Taodian 淘店中购买一个罗技 G102 游戏鼠标。
  验证方式：比较任务执行前后的订单数据，检查新订单是否匹配。
  """

  app_name = "taodian"

  complexity = 4.0

  _PROD_NAME = "罗技 G102 游戏鼠标"
  _PRODID = '220'
  _SKUID = '220001'
  _SHOPID = '1'
  _PROD_COUNT = 1
  _SNAPSHOT_NAME = "snapshot_9_long"

  @property
  def goal(self) -> str:
    return f"Buy the mouse that my friend recommended to me on {self.app_name} app. Payment password is 123456"

  @property
  def full_goal(self) -> str:
    return f"Buy a {self._PROD_NAME} on {self.app_name} app. Payment password is 123456"

  @property
  def information(self):
    return "Jessica Garcia texted me to recommend a mouse via simple sms messenger app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_orders = taodian_validator.get_orders(env)
    print(f"[DEBUG] Initializing taodian order mouse task...")
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