

"""固定任务：长任务集合。

包含以下任务：
- ClockSetAlarmForDelivery: 设置外卖送达前5分钟的闹钟
- BroccoliAddKungPaoChicken: 在食谱应用中添加宫保鸡丁食谱
- ExpenseRecordClothes: 记录一笔衣服消费
- TasksCreatePickup: 创建取快递待办
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import clock as clock_validator
from android_world.task_evals.custom_validators import expense as expense_validator
from android_world.task_evals.custom_validators import recipe as recipe_validator
from android_world.task_evals.custom_validators import task as task_validator


class User3Long_ClockSetAlarmForDelivery(fixed_task_eval.TaskEval):
  """固定任务：设置外卖送达前5分钟的闹钟。

  Agent 需要在 Clock 应用中设置一个19:25的闹钟。
  验证方式：通过 UI 检查闹钟是否被正确添加。
  """

  app_name = "clock"

  complexity = 4.0

  _ALARM_HOUR = 19
  _ALARM_MINUTE = 25
  _FUZZY_MINUTES = 1
  _SNAPSHOT_NAME = "snapshot_3_long"

  @property
  def goal(self) -> str:
    return f"Set an alarm for 5 minutes before Barbara Jones's food delivery arrives in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Set an alarm for {self._ALARM_HOUR:02d}:{self._ALARM_MINUTE:02d} in {self.app_name} app."

  @property
  def information(self):
    return "I ordered a '咖喱牛肉饭' (Beef Curry Rice) for Barbara Jones on tuantuanwaimai app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing clock set alarm for delivery task...")
    print(f"[DEBUG] Expected alarm: {self._ALARM_HOUR:02d}:{self._ALARM_MINUTE:02d}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = clock_validator.validate_alarm_added(
        env=env,
        expected_hour=self._ALARM_HOUR,
        expected_minute=self._ALARM_MINUTE,
        fuzzy_minutes=self._FUZZY_MINUTES,
    )
    return 1.0 if result else 0.0


class User3Long_BroccoliAddKungPaoChicken(fixed_task_eval.TaskEval):
  """固定任务：在食谱应用中添加宫保鸡丁食谱。

  Agent 需要在 Broccoli 食谱应用中添加一个宫保鸡丁食谱。
  验证方式：比较任务执行前后的食谱数据，检查新食谱是否匹配。
  """

  app_name = "broccoli"

  complexity = 4.0

  _RECIPE_TITLE = "Kung Pao Chicken"
  _RECIPE_DESCRIPTION = "A classic home-style Sichuan dish. The chicken is tender with a sweet, sour and slightly spicy taste. Paired with crispy peanuts, it is appetizing and goes well with rice."
  _SERVINGS = "2-3 people"
  _PREPARATION_TIME = "20 minutes"
  _INGREDIENTS = "250g chicken breast, 40g cooked peanuts, proper amount of dried chili peppers, scallions, ginger and garlic, Marinade: light soy sauce, cooking wine, a little starch, Sauce: light soy sauce, sugar, vinegar, water, starch."
  _DIRECTIONS = """1. Dice the chicken, add marinade and mix well. Marinate for ten minutes.
2. Chop scallions, ginger and garlic, then mix all seasonings to make the sauce.
3. Stir-fry diced chicken in hot oil until discolored and take out."""
  _SNAPSHOT_NAME = "snapshot_3_long"

  @property
  def goal(self) -> str:
    return f"Record the recipe someone sent me in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Add a recipe for '{self._RECIPE_TITLE}' to {self.app_name} app with the following details: Description: {self._RECIPE_DESCRIPTION}, Servings: {self._SERVINGS}, Preparation Time: {self._PREPARATION_TIME}, Ingredients: {self._INGREDIENTS}, Directions: {self._DIRECTIONS}"

  @property
  def information(self):
    return "I took a screenshot of the recipe someone sent me in simple gallery app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_recipes = recipe_validator.get_recipes(env)
    print(f"[DEBUG] Initializing broccoli add kung pao chicken task...")
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
        expected_description=self._RECIPE_DESCRIPTION,
        expected_servings=self._SERVINGS,
        expected_preparationTime=self._PREPARATION_TIME,
        expected_ingredients=self._INGREDIENTS,
        expected_directions=self._DIRECTIONS,
    )
    return 1.0 if result else 0.0


class User3Long_ExpenseRecordClothes(fixed_task_eval.TaskEval):
  """固定任务：在 Pro Expense 中记录衣服消费。

  Agent 需要在 Pro Expense 应用中记录一笔消费，
  金额是 139.99 元，类别是 clothes。
  验证方式：使用 LLM 判断记账记录是否符合要求。
  """

  app_name = "pro expense"

  complexity = 4.0

  _EXPENSE_NAME = "clothes"
  _EXPENSE_AMOUNT = 13999  # 139.99元，单位：分
  _CATEGORY = "Clothes"
  _SNAPSHOT_NAME = "snapshot_3_long"

  @property
  def goal(self) -> str:
    return f"Record my clothing purchase expense in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Record an expense in {self.app_name} app with amount {self._EXPENSE_AMOUNT / 100:.2f} yuan and category '{self._CATEGORY}'."

  @property
  def information(self):
    return "I bought two pieces of clothes on taodian app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_expenses = expense_validator.get_expenses(env)
    print(f"[DEBUG] Initializing expense record clothes task...")
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


class User3Long_TasksCreatePickup(fixed_task_eval.TaskEval):
  """固定任务：在 Tasks 中创建取快递待办。

  Agent 需要在 Tasks 应用中创建一个取快递待办，
  名字是取快递，取件码是23-2797。
  验证方式：使用 LLM 判断待办内容是否符合要求。
  """

  app_name = "tasks"

  complexity = 4.0

  _TASK_TITLE = "Pickup Package"
  _TASK_NOTES = "Pickup code: 23-2792"
  _SNAPSHOT_NAME = "snapshot_3_long"

  @property
  def goal(self) -> str:
    return f"Create a todo in {self.app_name} app for picking up my package. Write down the pickup code in Notes."

  @property
  def full_goal(self) -> str:
    return f"Create a todo in {self.app_name} app named '{self._TASK_TITLE}' with notes: {self._TASK_NOTES}."

  @property
  def information(self):
    return "Jessica Garcia texted me via simple sms messenger app that she bought me a package and told me the pickup code."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_tasks = task_validator.get_tasks(env)
    print(f"[DEBUG] Initializing tasks create pickup task...")
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