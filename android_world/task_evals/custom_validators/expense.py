

"""Tasks for managing expenses in an expense app."""

import abc
import dataclasses
import random
from typing import Any, Optional
from android_world.env import device_constants
from android_world.env import interface
from android_world.env.setup_device import apps
from android_world.task_evals import task_eval
from android_world.task_evals.common_validators import sqlite_validators
from android_world.task_evals.custom_validators import llm_as_judge
from android_world.task_evals.utils import sqlite_schema_utils
from android_world.task_evals.utils import sqlite_utils
from android_world.task_evals.utils import user_data_generation
from android_world.utils import datetime_utils
from android_world.utils import file_utils

_DB_PATH = '/data/data/com.arduia.expense/databases/accounting.db'
_TABLE_NAME = 'expense'
_APP_NAME = 'pro expense'
_DB_KEY = 'expense_id'

# How to represent recipes in text form.
_TEXT_REPRESENTATION_TYPE = 'text_representation_type'


EXPENSE_VALIDATION_PROMPT = """You are an expense validation assistant. Please determine whether the actual added expense meets the task requirements.

Task Requirements (Expected Expense):
- Name: {expected_name}
- Amount: {expected_amount}
- Category: {expected_category}

Actual Added Expense:
- Name: {actual_name}
- Amount: {actual_amount}
- Category: {actual_category}

Judgment Rules:
1. Judge holistically - consider the entire expense record as a whole
2. The actual expense is considered correct if it conveys the same core information as the expected expense
3. Extra fields in the actual expense are acceptable IF they are:
   - Repetitions or rephrasings of information already present in other fields
   - Natural elaborations that don't add new factual information
4. Missing fields in the actual expense are acceptable IF the information is implied by other fields
5. For amount: use semantic matching (e.g., "100" and "100.00" are equivalent, "1.5" and "1.50" are equivalent)
6. For category: use semantic matching (e.g., "Food" and "Dining" may be equivalent depending on context)
7. Note: Do NOT judge based on the note field. The note field is irrelevant and should be ignored.
8. Examples of SUCCESS:
   - Expected: Amount=1000, Actual: Amount=1000 -> SUCCESS (exact match)
9. Examples of FAILURE:
   - Expected: Name="Lunch", Actual: Name="Dinner" -> FAILURE (completely different expense)
   - Expected: Amount=1000, Actual: Amount=2000 -> FAILURE (different amount)
   - Expected: Name="Coffee", Actual: Name="Not specified" -> FAILURE (missing critical info)
10. Focus on semantic equivalence at the expense level, not strict field-by-field matching
"""


# ============================================================================
# 封装验证函数：检查记账操作是否成功
# ============================================================================

def get_expenses(env: interface.AsyncEnv) -> list[sqlite_schema_utils.Expense]:
    """获取所有记账记录列表。

    Args:
        env: Android 环境接口。

    Returns:
        Expense 对象列表。
    """
    expenses = sqlite_utils.get_rows_from_remote_device(
        _TABLE_NAME,
        _DB_PATH,
        sqlite_schema_utils.Expense,
        env,
    )
    # Debug: print all expenses with their attributes
    print(f"[DEBUG] get_expenses: found {len(expenses)} records")
    for i, exp in enumerate(expenses):
        print(f"[DEBUG]   Expense {i}: name={repr(exp.name)}, amount={exp.amount}, category={exp.category}, note={repr(exp.note)}")
    return expenses


def clear_expenses(env: interface.AsyncEnv) -> None:
    """清空所有记账记录。

    Args:
        env: Android 环境接口。
    """
    sqlite_utils.delete_all_rows_from_table(_TABLE_NAME, _DB_PATH, env, _APP_NAME)
    print("[DEBUG] All expenses cleared")


def add_expense_row(
    expense: sqlite_schema_utils.Expense,
    env: interface.AsyncEnv,
) -> None:
    """添加一条记账记录。

    Args:
        expense: 要添加的记账记录。
        env: Android 环境接口。
    """
    sqlite_utils.insert_rows_to_remote_db(
        [expense],
        _DB_KEY,
        _TABLE_NAME,
        _DB_PATH,
        _APP_NAME,
        env,
    )
    print(f"[DEBUG] Added expense: {expense.name}")


def _normalize_text(text: str) -> str:
    """标准化文本用于模糊匹配。"""
    return text.lower().strip()


def validate_expense_added(
    env: interface.AsyncEnv,
    goal: str,
    before_expenses: list[sqlite_schema_utils.Expense],
    expected_name: str,
    expected_amount: Optional[int] = None,
    expected_category: Optional[str] = None,
) -> bool:
    """验证单个记账记录是否被正确添加，使用 LLM 进行判断。

    Args:
        env: Android 环境接口。
        goal: 任务目标描述。
        before_expenses: 任务执行前的记账记录列表。
        expected_name: 期望的记账名称。
        expected_amount: 期望的金额（单位：分，可选）。
        expected_category: 期望的分类名称（可选）。

    Returns:
        True 如果验证通过，False 否则。
    """
    after_expenses = get_expenses(env)

    print(f"[DEBUG] Before expenses: {len(before_expenses)}")
    print(f"[DEBUG] After expenses: {len(after_expenses)}")
    print(f"[DEBUG] Expected: name='{expected_name}'")

    # 查找新增的记账记录
    before_ids = {e.expense_id for e in before_expenses}
    new_expenses = [e for e in after_expenses if e.expense_id not in before_ids]

    print(f"[DEBUG] New expenses count: {len(new_expenses)}")

    if not new_expenses:
        print("[DEBUG] No new expenses found, returning False")
        return False

    # 检查是否只添加了一个记账记录（验证数量正确性）
    if len(new_expenses) != 1:
        print(f"[DEBUG] Expected 1 new expense, but found {len(new_expenses)}. Validation failed.")
        return False

    # 打印新增记账记录详情
    print(f"[DEBUG] ========== New expenses ==========")
    for i, expense in enumerate(new_expenses):
        print(f"[DEBUG] New expense {i+1}:")
        print(f"[DEBUG]   name: {expense.name}")
        print(f"[DEBUG]   amount: {expense.amount}")
        print(f"[DEBUG]   category: {expense.category_name}")
        print(f"[DEBUG]   note: {expense.note}")

    # 取第一个新增记账记录进行验证
    actual_expense = new_expenses[0]

    # 构建 prompt
    prompt = EXPENSE_VALIDATION_PROMPT.format(
        expected_name=expected_name,
        expected_amount=expected_amount if expected_amount is not None else "Not specified",
        expected_category=expected_category if expected_category is not None else "Not specified",
        actual_name=actual_expense.name if actual_expense.name is not None else "Not specified",
        actual_amount=actual_expense.amount if actual_expense.amount is not None else "Not specified",
        actual_category=actual_expense.category_name if actual_expense.category_name is not None else "Not specified",
    )

    print(f"[DEBUG] Calling LLM to validate expense...")
    is_match, explanation = llm_as_judge.llm_judge(goal, prompt)
    print(f"[DEBUG] LLM judgment: {is_match}, Explanation: {explanation}")

    return is_match


def _expense_matches(
    expense: sqlite_schema_utils.Expense,
    name: Optional[str] = None,
    amount: Optional[int] = None,
    category: Optional[int] = None,
    note: Optional[str] = None,
    fuzzy_match_name: bool = True,
) -> bool:
    """检查记账记录是否匹配给定条件。

    Args:
        expense: 要检查的记账记录。
        name: 期望的名称。
        amount: 期望的金额（单位：分）。
        category: 期望的分类 ID。
        note: 期望的备注。
        fuzzy_match_name: 是否对名称使用模糊匹配。

    Returns:
        True 如果记账记录匹配所有提供的条件。
    """
    if name is not None:
        if fuzzy_match_name:
            if _normalize_text(expense.name) != _normalize_text(name):
                return False
        else:
            if expense.name != name:
                return False
    if amount is not None and expense.amount != amount:
        return False
    if category is not None and expense.category != category:
        return False
    if note is not None and expense.note != note:
        return False
    return True



def validate_expenses_added(
    env: interface.AsyncEnv,
    before_expenses: list[sqlite_schema_utils.Expense],
    expected_expenses: list[dict],
    check_integrity: bool = True,
    fuzzy_match_name: bool = True,
) -> bool:
    """验证多个记账记录是否被正确添加。

    Args:
        env: Android 环境接口。
        before_expenses: 任务执行前的记账记录列表。
        expected_expenses: 期望添加的记账记录列表，每个元素是包含 name, amount, category, note 等字段的字典。
        check_integrity: 是否检查其他记账记录完整性。
        fuzzy_match_name: 是否对名称使用模糊匹配。

    Returns:
        True 如果验证通过，False 否则。
    """
    after_expenses = get_expenses(env)

    print(f"[DEBUG] Before expenses: {len(before_expenses)}")
    print(f"[DEBUG] After expenses: {len(after_expenses)}")

    # 打印所有记账记录
    for i, expense in enumerate(after_expenses):
        print(f"[DEBUG] Expense {i}: name='{expense.name}', amount=${expense.amount / 100:.2f}")

    # 验证每个记账记录
    for exp_data in expected_expenses:
        # 只获取实际传入的字段，不强制要求 name 存在
        name = exp_data.get("name")
        amount = exp_data.get("amount")
        category = exp_data.get("category")
        note = exp_data.get("note")

        # 确保至少有一个条件被指定
        if name is None and amount is None and category is None and note is None:
            print(f"[DEBUG] No matching criteria provided in expected expense")
            return False

        debug_name = name if name is not None else "(any)"
        print(f"[DEBUG] Expected expense: name='{debug_name}', amount={amount}, category={category}, note={note}")

        # 查找匹配的记账记录
        found = False
        for expense in after_expenses:
            if _expense_matches(expense, name, amount, category, note, fuzzy_match_name):
                if expense not in before_expenses:
                    found = True
                    break

        if not found:
            print(f"[DEBUG] Failed to validate expense: name='{debug_name}', amount={amount}")
            return False

    # 检查数量是否正确
    if check_integrity:
        expected_count = len(expected_expenses)
        actual_count = len(after_expenses) - len(before_expenses)
        if actual_count != expected_count:
            print(f"[DEBUG] Count mismatch: expected {expected_count} new expenses, got {actual_count}")
            return False

    print(f"[DEBUG] Multiple expenses addition validated: True")
    return True


def validate_expense_deleted(
    env: interface.AsyncEnv,
    before_expenses: list[sqlite_schema_utils.Expense],
    expense_name: str,
    check_integrity: bool = True,
    fuzzy_match_name: bool = True,
) -> bool:
    """验证记账记录是否被正确删除。

    Args:
        env: Android 环境接口。
        before_expenses: 任务执行前的记账记录列表。
        expense_name: 要删除的记账记录名称。
        check_integrity: 是否检查其他记账记录完整性。
        fuzzy_match_name: 是否对名称使用模糊匹配。

    Returns:
        True 如果验证通过，False 否则。
    """
    after_expenses = get_expenses(env)

    print(f"[DEBUG] Before expenses: {len(before_expenses)}")
    print(f"[DEBUG] After expenses: {len(after_expenses)}")
    print(f"[DEBUG] Looking for expense to delete: name='{expense_name}'")

    # 查找要删除的记账记录
    expense_to_delete = None
    for expense in before_expenses:
        if fuzzy_match_name:
            if _normalize_text(expense.name) == _normalize_text(expense_name):
                expense_to_delete = expense
                break
        else:
            if expense.name == expense_name:
                expense_to_delete = expense
                break

    if expense_to_delete is None:
        print(f"[DEBUG] No expense found with name: {expense_name}")
        return False

    print(f"[DEBUG] Expense to delete: id={expense_to_delete.expense_id}, name='{expense_to_delete.name}'")

    # 检查记账记录是否已不在列表中
    if expense_to_delete in after_expenses:
        print(f"[DEBUG] Expense still exists in after_expenses")
        return False

    if check_integrity:
        # 验证其他记账记录未被修改
        for old_expense in before_expenses:
            if old_expense != expense_to_delete and old_expense not in after_expenses:
                return False
        if len(after_expenses) != len(before_expenses) - 1:
            return False

    print(f"[DEBUG] Expense deletion validated: True")
    return True


def validate_expense_modified(
    env: interface.AsyncEnv,
    before_expenses: list[sqlite_schema_utils.Expense],
    expense_name: str,
    expected_amount: Optional[int] = None,
    expected_category: Optional[int] = None,
    expected_note: Optional[str] = None,
    check_integrity: bool = True,
    fuzzy_match_name: bool = True,
) -> bool:
    """验证记账记录是否被正确修改。

    Args:
        env: Android 环境接口。
        before_expenses: 任务执行前的记账记录列表。
        expense_name: 要修改的记账记录名称（用于查找）。
        expected_amount: 期望的新金额（单位：分，可选）。
        expected_category: 期望的新分类 ID（可选）。
        expected_note: 期望的新备注（可选）。
        check_integrity: 是否检查其他记账记录完整性。
        fuzzy_match_name: 是否对名称使用模糊匹配。

    Returns:
        True 如果验证通过，False 否则。
    """
    after_expenses = get_expenses(env)

    print(f"[DEBUG] Before expenses: {len(before_expenses)}")
    print(f"[DEBUG] After expenses: {len(after_expenses)}")
    print(f"[DEBUG] Looking for expense to modify: name='{expense_name}'")

    # 查找要修改的记账记录
    expense_to_modify = None
    for expense in before_expenses:
        if fuzzy_match_name:
            if _normalize_text(expense.name) == _normalize_text(expense_name):
                expense_to_modify = expense
                break
        else:
            if expense.name == expense_name:
                expense_to_modify = expense
                break

    if expense_to_modify is None:
        print(f"[DEBUG] No expense found with name: {expense_name}")
        return False

    print(f"[DEBUG] Expense to modify: id={expense_to_modify.expense_id}, name='{expense_to_modify.name}', amount=${expense_to_modify.amount / 100:.2f}")

    # 在 after_expenses 中查找同一记录（通过 ID）
    modified_expense = None
    for expense in after_expenses:
        if expense.expense_id == expense_to_modify.expense_id:
            modified_expense = expense
            break

    if modified_expense is None:
        print(f"[DEBUG] Modified expense not found in after_expenses")
        return False

    print(f"[DEBUG] Found modified expense: amount=${modified_expense.amount / 100:.2f}, category={modified_expense.category_name}, note='{modified_expense.note}'")

    # 验证修改后的字段
    if expected_amount is not None:
        if modified_expense.amount != expected_amount:
            print(f"[DEBUG] Amount mismatch: expected ${expected_amount / 100:.2f}, got ${modified_expense.amount / 100:.2f}")
            return False
        print(f"[DEBUG] Amount validated: ${expected_amount / 100:.2f}")

    if expected_category is not None:
        if modified_expense.category != expected_category:
            print(f"[DEBUG] Category mismatch: expected {expected_category}, got {modified_expense.category}")
            return False
        print(f"[DEBUG] Category validated: {sqlite_schema_utils.Expense.category_id_to_name.get(expected_category, expected_category)}")

    if expected_note is not None:
        if modified_expense.note != expected_note:
            print(f"[DEBUG] Note mismatch: expected '{expected_note}', got '{modified_expense.note}'")
            return False
        print(f"[DEBUG] Note validated: '{expected_note}'")

    if check_integrity:
        # 验证其他记账记录未被修改
        for old_expense in before_expenses:
            if old_expense.expense_id != expense_to_modify.expense_id:
                # 检查该记录是否还在 after_expenses 中且未被修改
                found_in_after = False
                for after_expense in after_expenses:
                    if after_expense.expense_id == old_expense.expense_id:
                        found_in_after = True
                        if after_expense != old_expense:
                            print(f"[DEBUG] Other expense {old_expense.expense_id} was unexpectedly modified")
                            return False
                        break
                if not found_in_after:
                    print(f"[DEBUG] Other expense {old_expense.expense_id} was deleted")
                    return False

    print(f"[DEBUG] Expense modification validated: True")
    return True


def find_expense_by_name(
    expenses: list[sqlite_schema_utils.Expense],
    name: str,
    fuzzy_match: bool = True,
) -> Optional[sqlite_schema_utils.Expense]:
    """按名称查找记账记录。

    Args:
        expenses: 记账记录列表。
        name: 要搜索的名称。
        fuzzy_match: 是否使用模糊匹配。

    Returns:
        第一个匹配的记账记录，如果未找到则返回 None。
    """
    if fuzzy_match:
        normalized_name = _normalize_text(name)
        for expense in expenses:
            if _normalize_text(expense.name) == normalized_name:
                return expense
    else:
        for expense in expenses:
            if expense.name == name:
                return expense
    return None



def _get_expense_rows_as_text(
    rows: list[sqlite_schema_utils.Expense],
    format_type: str,
    wrap_width: int | None = None,
) -> str:
  return sqlite_schema_utils.get_text_representation_of_rows(
      rows,
      [
          'name',
          'amount_dollars',
          'category_name',
          'note',
      ],
      format_type,
      'name',
      wrap_width=wrap_width,
  )


def _ensure_db_exists(env: interface.AsyncEnv) -> None:
    """确保数据库表存在。"""
    if not sqlite_utils.table_exists(_TABLE_NAME, _DB_PATH, env):
        apps.ExpenseApp.setup(env)


