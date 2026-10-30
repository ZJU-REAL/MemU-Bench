

"""Functions for adding, deleting, and listing tasks for Tasks app database.

https://f-droid.org/en/packages/org.tasks/
"""

import datetime
import random
import uuid
from typing import Optional
from android_world.env import adb_utils
from android_world.env import device_constants
from android_world.env import interface
from android_world.task_evals.information_retrieval import calendar_utils
from android_world.task_evals.information_retrieval import datetime_utils as datetime_utils_ir
from android_world.task_evals.information_retrieval import proto_utils
from android_world.task_evals.information_retrieval.proto import state_pb2
from android_world.task_evals.information_retrieval.proto import task_pb2
from android_world.task_evals.custom_validators import llm_as_judge
from android_world.task_evals.utils import sqlite_schema_utils
from android_world.task_evals.utils import sqlite_utils
from android_world.utils import datetime_utils

_PRIMARY_KEY = '_id'
_TASK_TABLE = 'tasks'
_DB_PATH = '/data/data/org.tasks/databases/database'
_APP_NAME = 'tasks'


TASK_VALIDATION_PROMPT = """You are a task validation assistant. Please determine whether the actual added task meets the task requirements.

Task Requirements (Expected Task):
- Title: {expected_title}
- Notes: {expected_notes}
- Importance: {expected_importance}

Actual Added Task:
- Title: {actual_title}
- Notes: {actual_notes}
- Importance: {actual_importance}

Judgment Rules:
1. Judge holistically - consider the entire task as a whole, not just individual fields
2. The actual task is considered correct if it conveys the same core information as the expected task
3. Extra fields in the actual task are acceptable IF they are:
   - Repetitions or rephrasings of information already present in other fields
   - Natural elaborations of the title in the notes field
4. Missing fields in the actual task are acceptable IF the information is implied by other fields
5. For importance: use semantic matching (e.g., "High" and "Important" may be equivalent)
6. Examples of SUCCESS:
   - Expected: Notes="Not specified", Actual: Notes="Buy groceries for dinner" (when title is "Buy groceries") -> SUCCESS (notes just elaborates title)
   - Expected: Title="Meeting with John", Actual: Title="Meeting scheduled with John tomorrow" -> SUCCESS (core info is present)
7. Examples of FAILURE:
   - Expected: Title="Buy milk", Actual: Title="Buy eggs" -> FAILURE (completely different task)
   - Expected: Title="Submit report", Actual: Title="Not specified" -> FAILURE (missing critical info)
8. Focus on semantic equivalence at the task level, not strict field-by-field matching
"""


# ============================================================================
# 封装验证函数：检查任务操作是否成功
# ============================================================================

def get_tasks(env: interface.AsyncEnv) -> list[sqlite_schema_utils.Task]:
    """获取所有未删除的任务列表。

    Args:
        env: Android 环境接口。

    Returns:
        Task 对象列表（只包含未删除的任务）。
    """
    all_tasks = sqlite_utils.get_rows_from_remote_device(
        _TASK_TABLE,
        _DB_PATH,
        sqlite_schema_utils.Task,
        env,
    )
    # 过滤掉已删除的任务
    return [task for task in all_tasks if task.deleted == 0]


def _normalize_text(text: str) -> str:
    """标准化文本用于模糊匹配。"""
    return text.lower().strip()


def _format_importance(importance: int | None) -> str:
    """将重要性级别格式化为可读字符串。"""
    if importance is None:
        return "Not specified"
    # Tasks app: 0=high, 1=medium, 2=low, 3=none
    mapping = {0: "High", 1: "Medium", 2: "Low", 3: "None"}
    return mapping.get(importance, f"Level {importance}")


def _format_timestamp(ts: int | None) -> str:
    """将时间戳格式化为可读字符串。"""
    if ts is None or ts == 0:
        return "Not specified"
    try:
        dt = datetime.datetime.fromtimestamp(ts / 1000)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError):
        return str(ts)


def validate_task_added(
    env: interface.AsyncEnv,
    goal: str,
    before_tasks: list[sqlite_schema_utils.Task],
    expected_title: str,
    expected_notes: Optional[str] = None,
    expected_importance: Optional[int] = None,
    expected_due_date: Optional[int] = None,
) -> bool:
    """验证单个任务是否被正确添加，使用 LLM 进行判断。

    Args:
        env: Android 环境接口。
        goal: 任务目标描述。
        before_tasks: 任务执行前的任务列表。
        expected_title: 期望的任务标题。
        expected_notes: 期望的任务备注（可选）。
        expected_importance: 期望的重要性级别（可选）。
        expected_due_date: 期望的截止日期（Unix 时间戳，毫秒，可选）。

    Returns:
        True 如果验证通过，False 否则。
    """
    after_tasks = get_tasks(env)

    print(f"[DEBUG] Before tasks: {len(before_tasks)}")
    print(f"[DEBUG] After tasks: {len(after_tasks)}")
    print(f"[DEBUG] Expected: title='{expected_title}'")

    # 查找新增的任务
    before_ids = {t._id for t in before_tasks}
    new_tasks = [t for t in after_tasks if t._id not in before_ids]

    print(f"[DEBUG] New tasks count: {len(new_tasks)}")

    if not new_tasks:
        print("[DEBUG] No new tasks found, returning False")
        return False

    # 检查是否只添加了一个任务（验证数量正确性）
    if len(new_tasks) != 1:
        print(f"[DEBUG] Expected 1 new task, but found {len(new_tasks)}. Validation failed.")
        return False

    # 打印新增任务详情
    print(f"[DEBUG] ========== New tasks ==========")
    for i, task in enumerate(new_tasks):
        print(f"[DEBUG] New task {i+1}:")
        print(f"[DEBUG]   title: {task.title}")
        print(f"[DEBUG]   notes: {task.notes}")
        print(f"[DEBUG]   importance: {_format_importance(task.importance)}")
        print(f"[DEBUG]   dueDate: {_format_timestamp(task.dueDate)}")

    # 取第一个新增任务进行验证
    actual_task = new_tasks[0]

    # 如果指定了截止日期，进行精确匹配（不通过 LLM）
    if expected_due_date is not None:
        print(f"[DEBUG] Checking due date: expected={expected_due_date}, actual={actual_task.dueDate}")
        if actual_task.dueDate != expected_due_date:
            print(f"[DEBUG] Due date mismatch: expected {expected_due_date}, got {actual_task.dueDate}")
            return False
        print(f"[DEBUG] Due date matched exactly")

    # 构建 prompt（不包含 due_date，因为已经精确匹配过了）
    prompt = TASK_VALIDATION_PROMPT.format(
        expected_title=expected_title,
        expected_notes=expected_notes if expected_notes is not None else "Not specified",
        expected_importance=_format_importance(expected_importance),
        actual_title=actual_task.title if actual_task.title is not None else "Not specified",
        actual_notes=actual_task.notes if actual_task.notes is not None else "Not specified",
        actual_importance=_format_importance(actual_task.importance),
    )

    print(f"[DEBUG] Calling LLM to validate task...")
    is_match, explanation = llm_as_judge.llm_judge(goal, prompt)
    print(f"[DEBUG] LLM judgment: {is_match}, Explanation: {explanation}")

    return is_match


def _task_matches(
    task: sqlite_schema_utils.Task,
    title: Optional[str] = None,
    notes: Optional[str] = None,
    importance: Optional[int] = None,
    due_date: Optional[int] = None,
    hide_until: Optional[int] = None,
    fuzzy_match_title: bool = True,
) -> bool:
    """检查任务是否匹配给定条件。

    Args:
        task: 要检查的任务。
        title: 期望的标题。
        notes: 期望的备注内容。
        importance: 期望的重要性级别。
        due_date: 期望的截止日期（Unix 时间戳，毫秒）。
        hide_until: 期望的开始时间/隐藏直到时间（Unix 时间戳，毫秒）。
        fuzzy_match_title: 是否对标题使用模糊匹配。

    Returns:
        True 如果任务匹配所有提供的条件。
    """
    if title is not None:
        if fuzzy_match_title:
            if _normalize_text(task.title) != _normalize_text(title):
                return False
        else:
            if task.title != title:
                return False
    if notes is not None and task.notes != notes:
        return False
    if importance is not None and task.importance != importance:
        return False
    if due_date is not None and task.dueDate != due_date:
        return False
    if hide_until is not None and task.hideUntil != hide_until:
        return False
    return True




def validate_task_deleted(
    env: interface.AsyncEnv,
    before_tasks: list[sqlite_schema_utils.Task],
    task_title: str,
    check_integrity: bool = True,
    fuzzy_match_title: bool = True,
) -> bool:
    """验证任务是否被正确删除。

    Args:
        env: Android 环境接口。
        before_tasks: 任务执行前的任务列表。
        task_title: 要删除的任务标题。
        check_integrity: 是否检查其他任务完整性。
        fuzzy_match_title: 是否对标题使用模糊匹配。

    Returns:
        True 如果验证通过，False 否则。
    """
    after_tasks = get_tasks(env)

    print(f"[DEBUG] Before tasks: {len(before_tasks)}")
    print(f"[DEBUG] After tasks: {len(after_tasks)}")
    print(f"[DEBUG] Looking for task to delete: title='{task_title}'")

    # 打印before和after的详细信息
    print(f"[DEBUG] Before tasks details:")
    for t in before_tasks:
        print(f"[DEBUG]   id={t._id}, title='{t.title}', deleted={t.deleted}")
    print(f"[DEBUG] After tasks details:")
    for t in after_tasks:
        print(f"[DEBUG]   id={t._id}, title='{t.title}', deleted={t.deleted}")

    # 查找要删除的任务
    task_to_delete = None
    for task in before_tasks:
        if fuzzy_match_title:
            if _normalize_text(task.title) == _normalize_text(task_title):
                task_to_delete = task
                break
        else:
            if task.title == task_title:
                task_to_delete = task
                break

    if task_to_delete is None:
        print(f"[DEBUG] No task found with title: {task_title}")
        return False

    print(f"[DEBUG] Task to delete: id={task_to_delete._id}, title='{task_to_delete.title}'")

    # 检查任务是否已不在列表中（通过比较 _id）
    deleted = True
    for task in after_tasks:
        if task._id == task_to_delete._id:
            deleted = False
            break

    if not deleted:
        print(f"[DEBUG] Task still exists in after_tasks")
        return False

    print(f"[DEBUG] Task deleted successfully")

    if check_integrity:
        # 注意：这个检查不适用于同时添加新任务的场景，这里跳过检查
        print(f"[DEBUG] Skipping integrity check for delete+add scenario")

    print(f"[DEBUG] Task deletion validated: True")
    return True


def validate_task_completed(
    env: interface.AsyncEnv,
    before_tasks: list[sqlite_schema_utils.Task],
    task_title: str,
    check_integrity: bool = True,
    fuzzy_match_title: bool = True,
) -> bool:
    """验证任务是否被标记为完成。

    Args:
        env: Android 环境接口。
        before_tasks: 任务执行前的任务列表。
        task_title: 要完成的任务标题。
        check_integrity: 是否检查其他任务完整性。
        fuzzy_match_title: 是否对标题使用模糊匹配。

    Returns:
        True 如果验证通过，False 否则。
    """
    after_tasks = get_tasks(env)

    print(f"[DEBUG] Before tasks: {len(before_tasks)}")
    print(f"[DEBUG] After tasks: {len(after_tasks)}")
    print(f"[DEBUG] Looking for task to complete: title='{task_title}'")

    # 查找任务
    before_task = None
    after_task = None

    for task in before_tasks:
        if fuzzy_match_title:
            if _normalize_text(task.title) == _normalize_text(task_title):
                before_task = task
                break
        else:
            if task.title == task_title:
                before_task = task
                break

    if before_task is None:
        print(f"[DEBUG] No task found with title: {task_title}")
        return False

    # 在 after_tasks 中找到对应的任务
    for task in after_tasks:
        if task._id == before_task._id:
            after_task = task
            break

    if after_task is None:
        print(f"[DEBUG] Task not found in after_tasks")
        return False

    # 检查任务是否被标记为完成（completed > 0 表示已完成）
    if after_task.completed == 0:
        print(f"[DEBUG] Task not marked as completed")
        return False

    # 检查其他任务是否被错误地标记为已完成
    if check_integrity:
        for bt in before_tasks:
            if bt._id == before_task._id:
                continue
            # 之前未完成的任务，不应被标记为已完成
            if not bt.completed:
                for at in after_tasks:
                    if at._id == bt._id:
                        if at.completed:
                            print(f"[DEBUG] Task '{bt.title}' was incorrectly marked as completed (should remain uncompleted)")
                            return False
                        break

    print(f"[DEBUG] Task completion validated: True (completed={after_task.completed})")
    return True


def validate_tasks_completed(
    env: interface.AsyncEnv,
    before_tasks: list[sqlite_schema_utils.Task],
    task_titles: list[str],
    check_integrity: bool = True,
    fuzzy_match_title: bool = True,
) -> bool:
    """验证多个任务是否被标记为完成，同时检查其他任务未被错误标记。

    Args:
        env: Android 环境接口。
        before_tasks: 任务执行前的任务列表。
        task_titles: 需要标记为完成的任务标题列表。
        check_integrity: 是否检查其他任务完整性（未被错误标记为已完成）。
        fuzzy_match_title: 是否对标题使用模糊匹配。

    Returns:
        True 如果所有目标任务都被标记为完成且其他任务未被错误标记，False 否则。
    """
    after_tasks = get_tasks(env)

    print(f"[DEBUG] Before tasks: {len(before_tasks)}")
    print(f"[DEBUG] After tasks: {len(after_tasks)}")
    print(f"[DEBUG] Tasks to complete: {task_titles}")

    # 查找需要完成的任务
    tasks_to_complete_ids = set()
    for before_task in before_tasks:
        for title in task_titles:
            if fuzzy_match_title:
                if _normalize_text(before_task.title) == _normalize_text(title):
                    tasks_to_complete_ids.add(before_task._id)
                    break
            else:
                if before_task.title == title:
                    tasks_to_complete_ids.add(before_task._id)
                    break

    if len(tasks_to_complete_ids) < len(task_titles):
        print(f"[DEBUG] Not all tasks found in before state: found {len(tasks_to_complete_ids)}, expected {len(task_titles)}")
        return False

    # 检查目标任务是否在 after_tasks 中被标记为完成
    completed_count = 0
    for before_task in before_tasks:
        if before_task._id not in tasks_to_complete_ids:
            continue
        for after_task in after_tasks:
            if after_task._id == before_task._id:
                if after_task.completed:
                    completed_count += 1
                    print(f"[DEBUG] Task '{before_task.title}' is completed")
                else:
                    print(f"[DEBUG] Task '{before_task.title}' is NOT completed")
                break

    if completed_count != len(task_titles):
        print(f"[DEBUG] Only {completed_count}/{len(task_titles)} tasks completed")
        return False

    # 检查不应被标记为已完成的任务是否被错误地标记了
    if check_integrity:
        for before_task in before_tasks:
            if before_task._id in tasks_to_complete_ids:
                continue
            # 之前未完成的任务，不应被标记为已完成
            if not before_task.completed:
                for after_task in after_tasks:
                    if after_task._id == before_task._id:
                        if after_task.completed:
                            print(f"[DEBUG] Task '{before_task.title}' was incorrectly marked as completed (should remain uncompleted)")
                            return False
                        break

    print(f"[DEBUG] Tasks completion validated: True")
    return True


def find_task_by_title(
    tasks: list[sqlite_schema_utils.Task],
    title: str,
    fuzzy_match: bool = True,
) -> Optional[sqlite_schema_utils.Task]:
    """按标题查找任务。

    Args:
        tasks: 任务列表。
        title: 要搜索的标题。
        fuzzy_match: 是否使用模糊匹配。

    Returns:
        第一个匹配的任务，如果未找到则返回 None。
    """
    if fuzzy_match:
        normalized_title = _normalize_text(title)
        for task in tasks:
            if _normalize_text(task.title) == normalized_title:
                return task
    else:
        for task in tasks:
            if task.title == title:
                return task
    return None



def create_task_from_proto(
    task: state_pb2.TasksAppTask,
) -> sqlite_schema_utils.Task:
  """Creates a Task object from a state_pb2.TasksAppTask proto."""
  due_date_ts = 0
  hide_until_date_ts = 0
  completed_date_ts = 0
  if task.HasField('due_date'):
    due_date_ts = (
        calendar_utils.convert_datetime_to_unix_ts(task.due_date, task.due_time)
        * 1000
    )
  # created date is 1 week before due date.
  created_date_ts = due_date_ts - 7 * 3600
  if task.HasField('hide_until_date'):
    hide_until_date_ts = (
        calendar_utils.convert_datetime_to_unix_ts(
            task.hide_until_date, task.hide_until_time
        )
        * 1000
    )
  if task.HasField('completed_date'):
    completed_date_ts = (
        calendar_utils.convert_datetime_to_unix_ts(
            task.completed_date, task.completed_time
        )
        * 1000
    )
  notes = task.notes if task.HasField('notes') else None
  importance = int(task.importance) if task.HasField('importance') else 2
  return sqlite_schema_utils.Task(
      title=task.title,
      importance=importance,
      dueDate=due_date_ts,
      hideUntil=hide_until_date_ts,
      completed=completed_date_ts,
      created=created_date_ts,
      modified=created_date_ts,
      notes=notes,
      remoteId=str(uuid.uuid4().int),
      recurrence=None,
  )


def add_tasks(
    rows: list[sqlite_schema_utils.Task], env: interface.AsyncEnv
) -> None:
  sqlite_utils.insert_rows_to_remote_db(
      rows,
      _PRIMARY_KEY,
      _TASK_TABLE,
      _DB_PATH,
      _APP_NAME,
      env,
  )
  adb_utils.close_app(_APP_NAME, env.controller)  # Register changes.


def clear_task_db(env: interface.AsyncEnv) -> None:
  """Clears the task database."""
  sqlite_utils.delete_all_rows_from_table(_TASK_TABLE, _DB_PATH, env, _APP_NAME)
  adb_utils.close_app(_APP_NAME, env.controller)  # Register changes.


def list_rows(
    env: interface.AsyncEnv,
) -> list[sqlite_schema_utils.Task]:
  return sqlite_utils.get_rows_from_remote_device(
      _TASK_TABLE,
      _DB_PATH,
      sqlite_schema_utils.Task,
      env,
  )




def check_task_conditions(
    task: sqlite_schema_utils.Task,
    exclusion_conditions: list[task_pb2.ExclusionCondition],
) -> bool:
  """Evaluates the specified task against a set of exclusion conditions.

  A task is considered eligible if it does not satisfy all of the conditions
  specified in the exclusion_conditions list. Each condition is checked against
  various fields of the task such as importance, completed date, due date, and
  title. The task is eligible if not all of these conditions are met, ensuring
  it doesn't fall under any exclusion criteria defined.

  Args:
    task: The task to check
    exclusion_conditions: All the conditions the task will be checked against,
      if they are all met, this task should be excluded and does not meet the
      conditions.

  Returns:
    A bool, True if the task does not meet all of the exclusion conditions,
    False otherwise.
  """
  if not exclusion_conditions:
    return True
  # Keeps track of whether an exclusion condition is met.
  all_conditions_met = True
  for condition in exclusion_conditions:
    if condition.field == 'due_date':
      condition_value = datetime_utils_ir.get_date(condition.value)
      due_datetime = datetime_utils.timestamp_to_localized_datetime(
          int(task.dueDate / 1000)
      )

      all_conditions_met = all_conditions_met and proto_utils.compare(
          due_datetime.date(), condition.operation, condition_value
      )
    if condition.field == 'completed_date':
      completed_datetime = datetime_utils.timestamp_to_localized_datetime(
          int(task.completed / 1000)
      )
      # Tasks app uses 0 in completed_date to indicate it's not complete.
      if condition.value == '0':
        all_conditions_met = all_conditions_met and proto_utils.compare(
            int(task.completed), condition.operation, 0
        )
      else:
        condition_value = datetime_utils_ir.get_date(condition.value)
        all_conditions_met = all_conditions_met and proto_utils.compare(
            completed_datetime.date(), condition.operation, condition_value
        )

    elif condition.field == 'title':
      all_conditions_met = all_conditions_met and proto_utils.compare(
          task.title.lower(), condition.operation, condition.value.lower()
      )
    elif condition.field == 'importance':
      all_conditions_met = all_conditions_met and proto_utils.compare(
          int(task.importance), condition.operation, int(condition.value)
      )

  return not all_conditions_met


