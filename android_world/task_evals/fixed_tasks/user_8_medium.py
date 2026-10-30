

"""固定任务：中等任务集合。

包含以下任务：
- TasksCreateTuition: 创建交学费待办
- BroccoliOpenGreekSalad: 打开Greek Salad Pita Pockets食谱
- BroccoliAddChiliFriedPorkNoodles: 添加辣炒猪肉面条食谱
- CalendarAddNeighborhoodWalk: 创建neighborhood walk日程
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import calendar as calendar_validator
from android_world.task_evals.custom_validators import recipe as recipe_validator
from android_world.task_evals.custom_validators import task as task_validator


class User8Medium_TasksCreateTuition(fixed_task_eval.TaskEval):
  """固定任务：在 Tasks 中创建交学费待办。

  Agent 需要在 Tasks 应用中创建一个交学费待办，
  名字是 pay tuition fee，截止日期是6月16日。
  验证方式：使用 LLM 判断待办内容是否符合要求。
  """

  app_name = "tasks"

  complexity = 4.0

  _TASK_TITLE = "pay tuition fee 5000 yuan"
  _DUE_DATE = "2026-06-16"
  _DUE_DATE_TS = 1781611200000  # 2026-06-16
  _SNAPSHOT_NAME = "snapshot_8_medium"

  @property
  def goal(self) -> str:
    return f"I paid this month's tuition, create a todo in {self.app_name} app for tuition payment with the same amount as this payment, and due date the same day next month."

  @property
  def full_goal(self) -> str:
    return f"Create a todo in {self.app_name} app named '{self._TASK_TITLE}' with due date {self._DUE_DATE}."

  @property
  def information(self):
    return "I recorded a tuition payment expense in pro expense app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_tasks = task_validator.get_tasks(env)
    print(f"[DEBUG] Initializing tasks create tuition task...")
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


class User8Medium_BroccoliOpenGreekSalad(fixed_task_eval.TaskEval):
  """固定任务：打开Greek Salad Pita Pockets食谱。

  Agent 需要在 Broccoli 食谱应用中打开 Greek Salad Pita Pockets 食谱。
  验证方式：检查食谱应用是否在前景且显示了正确的食谱。
  """

  app_name = "broccoli"

  complexity = 4.0

  _RECIPE_TITLE = "Greek Salad Pita Pockets"
  _SNAPSHOT_NAME = "snapshot_8_medium"

  @property
  def goal(self) -> str:
    return f"Open the recipe for the dish I'm making tonight in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Open the {self._RECIPE_TITLE} recipe in {self.app_name} app."

  @property
  def information(self):
    return "I texted with William Smith via simple sms messenger app about what dish to make tonight."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing broccoli open greek salad task...")
    print(f"[DEBUG] Expected recipe: {self._RECIPE_TITLE}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = recipe_validator.validate_recipe_opened(
        env=env,
        expected_title=self._RECIPE_TITLE,
        fuzzy_match=True,
        required_texts="various amounts"
    )
    return 1.0 if result else 0.0


class User8Medium_BroccoliAddChiliFriedPorkNoodles(fixed_task_eval.TaskEval):
  """固定任务：在 Broccoli 中添加辣炒猪肉面条食谱。

  Agent 需要在 Broccoli 食谱应用中创建一个新食谱：
  - 标题：Chili Fried Pork Noodles
  - 食材：Fresh noodles 1 bunch, pork 150g, 4 green peppers, 2 garlic cloves
  - 调味品：2 tbsp light soy sauce, 0.5 tbsp dark soy sauce, a pinch of salt, 1 tbsp oyster sauce, cooking oil
  - 步骤：
    1. Slice the pork, cut green peppers into strips, slice garlic.
    2. Boil water, cook the noodles. Take out, rinse with cold water and drain.
    3. Heat oil in a pan, stir-fry pork until discolored and oily.
    4. Add garlic, stir until fragrant. Pour in dark soy sauce, light soy sauce and oyster sauce.
    5. Add green peppers and stir-fry until half-cooked, add salt to taste.
    6. Add the noodles, stir well over high heat and serve.
  验证方式：使用 LLM 判断食谱内容是否符合要求。
  """

  app_name = "broccoli"

  complexity = 4.0

  _RECIPE_TITLE = "Chili Fried Pork Noodles"
  _INGREDIENTS = "Fresh noodles 1 bunch, pork 150g, 4 green peppers, 2 garlic cloves. 2 tbsp light soy sauce, 0.5 tbsp dark soy sauce, a pinch of salt, 1 tbsp oyster sauce, cooking oil"
  _DIRECTIONS = ("1. Slice the pork, cut green peppers into strips, slice garlic. "
                 "2. Boil water, cook the noodles. Take out, rinse with cold water and drain. "
                 "3. Heat oil in a pan, stir-fry pork until discolored and oily. "
                 "4. Add garlic, stir until fragrant. Pour in dark soy sauce, light soy sauce and oyster sauce. "
                 "5. Add green peppers and stir-fry until half-cooked, add salt to taste. "
                 "6. Add the noodles, stir well over high heat and serve.")
  _SNAPSHOT_NAME = "snapshot_8_medium"

  @property
  def goal(self) -> str:
    return f"Record the recipe that a friend recommended in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return (f"Create a recipe in {self.app_name} app with title '{self._RECIPE_TITLE}', "
            f"ingredients: {self._INGREDIENTS}, "
            f"and directions: {self._DIRECTIONS}")

  @property
  def information(self):
    return "Jennifer Smith texted to recommend a dish via simple sms messenger app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_recipes = recipe_validator.get_recipes(env)
    print(f"[DEBUG] Initializing broccoli add chili fried pork noodles task...")
    print(f"[DEBUG] Before recipes: {len(self._before_recipes)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_recipes'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = recipe_validator.validate_recipe_added(
        env=env,
        goal=self.full_goal,
        before_recipes=self._before_recipes,
        expected_title=self._RECIPE_TITLE,
        expected_ingredients=self._INGREDIENTS,
        expected_directions=self._DIRECTIONS,
    )
    return 1.0 if result else 0.0


class User8Medium_CalendarAddNeighborhoodWalk(fixed_task_eval.TaskEval):
  """固定任务：在日历中创建 neighborhood walk 日程。

  Agent 需要在日历应用中创建一个日程：
  - 标题：neighborhood walk 5.28 mile
  - 日期：2026年5月20日
  验证方式：检查日历事件是否正确创建。
  """

  app_name = "simple calendar"

  complexity = 4.0

  _EVENT_TITLE = "neighborhood walk 5.28 mile"
  _EVENT_DATE = "2026-05-20"
  _EVENT_START_TS = 1779303600  # 2026-05-20 19:00 UTC
  _EVENT_END_TS = 1779314400  # 2026-05-20 22:00 UTC
  _SNAPSHOT_NAME = "snapshot_8_medium"

  @property
  def goal(self) -> str:
    return f"I haven't done a neighborhood walk in a while, create a calendar event for it in {self.app_name} app, name it 'neighborhood walk X mile', the mile is twice my last neighborhood walk, date is May 20. Time: 7 p.m. to 10 p.m."

  @property
  def full_goal(self) -> str:
    return f"Create a calendar event in {self.app_name} app with title '{self._EVENT_TITLE}' on {self._EVENT_DATE}. Time: 7 p.m. to 10 p.m."

  @property
  def information(self):
    return "My last neighborhood walk distance is recorded in open tracks app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_events = calendar_validator.get_current_events(env)
    print(f"[DEBUG] Initializing calendar add neighborhood walk task...")
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
        expected_end_ts=self._EVENT_END_TS,
    )
    return 1.0 if result else 0.0