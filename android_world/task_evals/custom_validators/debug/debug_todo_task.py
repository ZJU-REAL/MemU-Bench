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

"""Debug evaluators for Tasks (Todo) app tasks.

These evaluators verify task operations (add/delete/complete) by checking
the underlying SQLite database.

The Tasks app: https://f-droid.org/en/packages/org.tasks/
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import task as task_validator
from android_world.task_evals.information_retrieval import task_app_utils
from android_world.task_evals.utils import sqlite_schema_utils


class DebugTaskAdd(fixed_task_eval.TaskEval):
  """固定任务：验证待办事项是否被添加。

  Agent 需要在 Tasks 应用中添加一个待办事项。
  验证方式：比较任务执行前后的数据库状态。
  """

  complexity = 1.0

  # 固定的任务参数
  _TASK_TITLE = "Buy groceries"
  _TASK_NOTES = "Milk, eggs, bread, and cheese"

  @property
  def goal(self) -> str:
    """任务目标。"""
    return f"In the Tasks app, create a new task titled '{self._TASK_TITLE}' with notes '{self._TASK_NOTES}'"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空数据库，存储初始状态。"""
    print("[DEBUG] Clearing Tasks database...")
    task_app_utils.clear_task_db(env)
    print("[DEBUG] Tasks database cleared")
    self._before_tasks = task_validator.get_tasks(env)
    print(f"[DEBUG] Stored before state: {len(self._before_tasks)} tasks")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_tasks'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = task_validator.validate_task_added(
        env=env,
        before_tasks=self._before_tasks,
        expected_title=self._TASK_TITLE,
        expected_notes=self._TASK_NOTES,
    )
    return 1.0 if result else 0.0


class DebugTaskDelete(fixed_task_eval.TaskEval):
  """固定任务：验证待办事项是否被删除。

  Agent 需要在 Tasks 应用中删除指定的待办事项。
  验证方式：比较任务执行前后的数据库状态。
  """

  complexity = 1.0

  # 固定的任务标题
  _TASK_TITLE = "Buy groceries"

  @property
  def goal(self) -> str:
    """任务目标。"""
    return f"In the Tasks app, delete the task titled '{self._TASK_TITLE}'"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空数据库，添加预设任务，存储初始状态。"""
    print("[DEBUG] Clearing Tasks database...")
    task_app_utils.clear_task_db(env)
    print("[DEBUG] Tasks database cleared")

    # 添加预设任务
    print(f"[DEBUG] Adding preset task: {self._TASK_TITLE}")
    preset_task = sqlite_schema_utils.Task(
        title=self._TASK_TITLE,
        notes="Milk, eggs, bread, and cheese",
    )
    task_app_utils.add_tasks([preset_task], env)
    print("[DEBUG] Preset task added")

    self._before_tasks = task_validator.get_tasks(env)
    print(f"[DEBUG] Stored before state: {len(self._before_tasks)} tasks")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_tasks'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = task_validator.validate_task_deleted(
        env=env,
        before_tasks=self._before_tasks,
        task_title=self._TASK_TITLE,
    )
    return 1.0 if result else 0.0


class DebugTaskComplete(fixed_task_eval.TaskEval):
  """固定任务：验证待办事项是否被标记为完成。

  Agent 需要在 Tasks 应用中标记指定的待办事项为完成。
  验证方式：比较任务执行前后的数据库状态。
  """

  complexity = 1.0

  # 固定的任务标题
  _TASK_TITLE = "Buy groceries"

  @property
  def goal(self) -> str:
    """任务目标。"""
    return f"In the Tasks app, mark the task '{self._TASK_TITLE}' as completed"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空数据库，添加预设任务，存储初始状态。"""
    print("[DEBUG] Clearing Tasks database...")
    task_app_utils.clear_task_db(env)
    print("[DEBUG] Tasks database cleared")

    # 添加预设任务（未完成状态）
    print(f"[DEBUG] Adding preset task: {self._TASK_TITLE}")
    preset_task = sqlite_schema_utils.Task(
        title=self._TASK_TITLE,
        notes="Milk, eggs, bread, and cheese",
        completed=0,  # 未完成
    )
    task_app_utils.add_tasks([preset_task], env)
    print("[DEBUG] Preset task added")

    self._before_tasks = task_validator.get_tasks(env)
    print(f"[DEBUG] Stored before state: {len(self._before_tasks)} tasks")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_tasks'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = task_validator.validate_task_completed(
        env=env,
        before_tasks=self._before_tasks,
        task_title=self._TASK_TITLE,
    )
    return 1.0 if result else 0.0


class DebugTaskAddMultiple(fixed_task_eval.TaskEval):
  """固定任务：验证多个待办事项是否被添加。

  Agent 需要在 Tasks 应用中添加多个待办事项。
  验证方式：比较任务执行前后的数据库状态。
  """

  complexity = 1.5

  # 固定的任务参数
  _TASKS = [
      {"title": "Buy groceries", "notes": "Milk, eggs, bread"},
      {"title": "Call mom", "notes": "Ask about weekend plans"},
  ]

  @property
  def goal(self) -> str:
    """任务目标。"""
    return ("In the Tasks app, create two tasks: 'Buy groceries' with notes about grocery items, "
            "and 'Call mom' with notes about weekend plans")

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空数据库，存储初始状态。"""
    print("[DEBUG] Clearing Tasks database...")
    task_app_utils.clear_task_db(env)
    print("[DEBUG] Tasks database cleared")
    self._before_tasks = task_validator.get_tasks(env)
    print(f"[DEBUG] Stored before state: {len(self._before_tasks)} tasks")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_tasks'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = task_validator.validate_tasks_added(
        env=env,
        before_tasks=self._before_tasks,
        expected_tasks=self._TASKS,
    )
    return 1.0 if result else 0.0