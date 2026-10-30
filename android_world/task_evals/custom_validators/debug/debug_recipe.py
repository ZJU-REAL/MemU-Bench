# Copyright 2026 The android_world Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Debug evaluators for Broccoli Recipe app tasks.

These evaluators verify recipe operations by checking
the SQLite database directly.
"""

import time
from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import recipe as recipe_validator


class DebugRecipeAdd(fixed_task_eval.TaskEval):
  """固定任务：验证食谱是否被正确添加。

  Agent 需要在 Broccoli 应用中添加指定食谱。
  验证方式：检查 SQLite 数据库中的食谱数据。
  """

  complexity = 2.0

  # 固定的食谱参数
  _EXPECTED_RECIPE = {
      "title": "Spicy Tuna Wraps",
      "description": "A quick and easy meal",
      "servings": "2 servings",
      "preparationTime": "20 mins",
      "ingredients": "see directions",
  }

  @property
  def goal(self) -> str:
    """任务目标。"""
    return f"In the Broccoli app, add a recipe titled '{self._EXPECTED_RECIPE['title']}'"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空已有食谱，记录初始状态。"""
    print("[DEBUG] Clearing existing recipes...")
    recipe_validator.clear_recipes(env)
    time.sleep(1)
    print("[DEBUG] Recording initial state...")
    self._before_recipes = recipe_validator.get_recipes(env)
    print(f"[DEBUG] Stored before state: {len(self._before_recipes)} recipes")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_recipes'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = recipe_validator.validate_recipe_added(
        env=env,
        before_recipes=self._before_recipes,
        expected=self._EXPECTED_RECIPE,
    )
    return 1.0 if result else 0.0


class DebugRecipeAddMultiple(fixed_task_eval.TaskEval):
  """固定任务：验证多个食谱是否被正确添加。

  Agent 需要在 Broccoli 应用中添加多个食谱。
  验证方式：检查 SQLite 数据库中的食谱数据。
  """

  complexity = 2.5

  # 固定的食谱参数
  _EXPECTED_RECIPES = [
      {
          "title": "Spicy Tuna Wraps",
          "servings": "2 servings",
          "preparationTime": "20 mins",
      },
      {
          "title": "Avocado Toast with Egg",
          "servings": "1 serving",
          "preparationTime": "10 mins",
      },
  ]

  @property
  def goal(self) -> str:
    """任务目标。"""
    titles = [r['title'] for r in self._EXPECTED_RECIPES]
    return f"In the Broccoli app, add recipes: {', '.join(titles)}"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空已有食谱，记录初始状态。"""
    print("[DEBUG] Clearing existing recipes...")
    recipe_validator.clear_recipes(env)
    time.sleep(1)
    print("[DEBUG] Recording initial state...")
    self._before_recipes = recipe_validator.get_recipes(env)
    print(f"[DEBUG] Stored before state: {len(self._before_recipes)} recipes")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_recipes'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = recipe_validator.validate_recipes_added(
        env=env,
        before_recipes=self._before_recipes,
        expected_list=self._EXPECTED_RECIPES,
    )
    return 1.0 if result else 0.0


class DebugRecipeDelete(fixed_task_eval.TaskEval):
  """固定任务：验证食谱是否被正确删除。

  Agent 需要在 Broccoli 应用中删除指定食谱。
  验证方式：检查 SQLite 数据库中的食谱数据。
  """

  complexity = 2.0

  # 要删除的食谱标题
  _TARGET_TITLE = "Spicy Tuna Wraps"

  @property
  def goal(self) -> str:
    """任务目标。"""
    return f"In the Broccoli app, delete the recipe titled '{self._TARGET_TITLE}'"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空数据库并添加目标食谱，记录初始状态。"""
    print("[DEBUG] Clearing existing recipes...")
    recipe_validator.clear_recipes(env)
    time.sleep(1)
    print("[DEBUG] Recording initial state...")
    self._before_recipes = recipe_validator.get_recipes(env)
    print(f"[DEBUG] Stored before state: {len(self._before_recipes)} recipes")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_recipes'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    expected = {"title": self._TARGET_TITLE}
    result = recipe_validator.validate_recipe_deleted(
        env=env,
        before_recipes=self._before_recipes,
        expected=expected,
    )
    return 1.0 if result else 0.0


class DebugRecipeDeleteMultiple(fixed_task_eval.TaskEval):
  """固定任务：验证多个食谱是否被正确删除。

  Agent 需要在 Broccoli 应用中删除多个食谱。
  验证方式：检查 SQLite 数据库中的食谱数据。
  """

  complexity = 2.5

  # 要删除的食谱标题列表
  _TARGET_TITLES = ["Spicy Tuna Wraps", "Avocado Toast with Egg"]

  @property
  def goal(self) -> str:
    """任务目标。"""
    return f"In the Broccoli app, delete recipes: {', '.join(self._TARGET_TITLES)}"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空数据库并添加目标食谱，记录初始状态。"""
    print("[DEBUG] Clearing existing recipes...")
    recipe_validator.clear_recipes(env)
    time.sleep(1)
    print("[DEBUG] Recording initial state...")
    self._before_recipes = recipe_validator.get_recipes(env)
    print(f"[DEBUG] Stored before state: {len(self._before_recipes)} recipes")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_recipes'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    expected_list = [{"title": t} for t in self._TARGET_TITLES]
    result = recipe_validator.validate_recipes_deleted(
        env=env,
        before_recipes=self._before_recipes,
        expected_list=expected_list,
    )
    return 1.0 if result else 0.0


