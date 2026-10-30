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

"""Debug evaluators for Expense (记账) app tasks.

These evaluators verify expense operations (add/delete) by checking
the underlying SQLite database.

The Expense app: Pro Expense Tracker
"""

from android_world.env import interface
from android_world.env.setup_device import apps
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import expense as expense_validator
from android_world.task_evals.utils import sqlite_schema_utils
from android_world.task_evals.utils import sqlite_utils


_APP_NAME = 'pro expense'
_DB_PATH = '/data/data/com.arduia.expense/databases/accounting.db'
_TABLE_NAME = 'expense'


def _ensure_db_exists(env: interface.AsyncEnv) -> None:
    """确保数据库表存在。"""
    if not sqlite_utils.table_exists(_TABLE_NAME, _DB_PATH, env):
        apps.ExpenseApp.setup(env)


class DebugExpenseAdd(fixed_task_eval.TaskEval):
  """固定任务：验证记账记录是否被添加。

  Agent 需要在 Pro Expense 应用中添加一条记账记录。
  验证方式：比较任务执行前后的数据库状态。
  """

  complexity = 1.0

  # 固定的记账参数
  _EXPENSE_NAME = "Lunch"
  _EXPENSE_AMOUNT = 1500  # $15.00 (单位：分)
  _EXPENSE_CATEGORY = 3  # Food
  _EXPENSE_NOTE = "Team lunch at restaurant"

  @property
  def goal(self) -> str:
    """任务目标。"""
    return (f"In the Pro Expense app, add an expense named '{self._EXPENSE_NAME}' "
            f"with amount ${self._EXPENSE_AMOUNT / 100:.2f} in the Food category, "
            f"with note '{self._EXPENSE_NOTE}'")

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空数据库，存储初始状态。"""
    print("[DEBUG] Initializing expense task...")
    _ensure_db_exists(env)
    expense_validator.clear_expenses(env)
    print("[DEBUG] Expenses cleared")
    self._before_expenses = expense_validator.get_expenses(env)
    print(f"[DEBUG] Stored before state: {len(self._before_expenses)} expenses")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_expenses'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = expense_validator.validate_expense_added(
        env=env,
        before_expenses=self._before_expenses,
        expected_name=self._EXPENSE_NAME,
        expected_amount=self._EXPENSE_AMOUNT,
        expected_category=self._EXPENSE_CATEGORY,
        expected_note=self._EXPENSE_NOTE,
    )
    return 1.0 if result else 0.0





class DebugExpenseAddMultiple(fixed_task_eval.TaskEval):
  """固定任务：验证多条记账记录是否被添加。

  Agent 需要在 Pro Expense 应用中添加多条记账记录。
  验证方式：比较任务执行前后的数据库状态。
  """

  complexity = 1.5

  # 固定的记账参数
  _EXPENSES = [
      {"name": "Coffee", "amount": 500, "category": 3},  # $5.00, Food
      {"name": "Bus ticket", "amount": 250, "category": 7},  # $2.50, Transportation
  ]

  @property
  def goal(self) -> str:
    """任务目标。"""
    return ("In the Pro Expense app, add two expenses: "
            "'Coffee' for $5.00 in Food category, and "
            "'Bus ticket' for $2.50 in Transportation category")

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空数据库，存储初始状态。"""
    print("[DEBUG] Initializing expense task...")
    _ensure_db_exists(env)
    expense_validator.clear_expenses(env)
    print("[DEBUG] Expenses cleared")
    self._before_expenses = expense_validator.get_expenses(env)
    print(f"[DEBUG] Stored before state: {len(self._before_expenses)} expenses")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_expenses'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = expense_validator.validate_expenses_added(
        env=env,
        before_expenses=self._before_expenses,
        expected_expenses=self._EXPENSES,
    )
    return 1.0 if result else 0.0


class DebugExpenseModify(fixed_task_eval.TaskEval):
  """固定任务：验证记账记录是否被修改。

  Agent 需要在 Pro Expense 应用中修改一条已存在的记账记录。
  验证方式：比较任务执行前后的数据库状态。
  """

  complexity = 1.5

  # 原始记账记录
  _ORIGINAL_EXPENSE = sqlite_schema_utils.Expense(
      expense_id=1,
      name="Lunch",
      amount=1500,  # $15.00
      category=3,  # Food
      note="Original lunch expense",
  )

  # 期望修改后的值
  _EXPECTED_AMOUNT = 3000  # $30.00
  _EXPECTED_CATEGORY = 3  # Food (keep same)

  @property
  def goal(self) -> str:
    """任务目标。"""
    return (f"In the Pro Expense app, modify the expense named '{self._ORIGINAL_EXPENSE.name}' "
            f"to change the amount from $15.00 to $30.00")

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空数据库，添加预设记账记录。"""
    print("[DEBUG] Initializing expense modify task...")
    _ensure_db_exists(env)
    expense_validator.clear_expenses(env)
    print("[DEBUG] Expenses cleared")

    # 添加原始记账记录
    expense_validator.add_expense_row(self._ORIGINAL_EXPENSE, env)
    print(f"[DEBUG] Added original expense: {self._ORIGINAL_EXPENSE.name} with amount ${self._ORIGINAL_EXPENSE.amount / 100:.2f}")

    self._before_expenses = expense_validator.get_expenses(env)
    print(f"[DEBUG] Stored before state: {len(self._before_expenses)} expenses")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_expenses'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = expense_validator.validate_expense_modified(
        env=env,
        before_expenses=self._before_expenses,
        expense_name=self._ORIGINAL_EXPENSE.name,
        expected_amount=self._EXPECTED_AMOUNT,
    )
    return 1.0 if result else 0.0


