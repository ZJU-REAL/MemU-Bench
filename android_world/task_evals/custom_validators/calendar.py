

"""Evaluators for Simple Calendar Pro.

They look at the underlying state of the sqlite database.
"""

import difflib
from datetime import datetime, timezone, timedelta
from absl import logging
from android_world.task_evals.custom_validators import llm_as_judge
from android_world.task_evals.utils import sqlite_schema_utils


# Threshold for determining if two strings are equal using
# difflib.SequenceMatcher(...).ratio().
_MIN_DIFF_SIMILARITY = 0.9


def fuzzy_match(text1: str, text2: str, ignore_case: bool = True) -> bool:
  """Compares two strings.

  Args:
    text1: The first text.
    text2: The second text.
    ignore_case: Whether to ignore case during comparison.

  Returns:
    Whether the two strings are approximately equal.
  """
  if text1 is None or text2 is None:
    return False
  text1 = str(text1)
  text2 = str(text2)

  def text_similarity(text1: str, text2: str, ignore_case: bool) -> float:
    """Computes similiarity between two texts."""
    if ignore_case:
      text1 = text1.lower()
      text2 = text2.lower()

    return difflib.SequenceMatcher(None, text1, text2).ratio()
  return (
      text_similarity(text1, text2, ignore_case=ignore_case)
      >= _MIN_DIFF_SIMILARITY
  )


def validate_rows_removal_integrity(
    before: list[sqlite_schema_utils.RowType],
    after: list[sqlite_schema_utils.RowType],
    ids: list[int],
    id_name: str,
) -> bool:
  """Validates that specified rows have been removed correctly from the rows list and that the remaining rows are unaltered.

  This function checks that all rows with IDs in `ids` are not present
  in the `after` state and that all other rows from the `before` state remain
  unchanged. It also ensures that no new rows have been inadvertently added.

  Args:
    before: State of the rows before removal.
    after: State of the rows after attempted removal.
    ids: IDs of the rows expected to be removed.
    id_name: The name of the ID column in the database.

  Returns:
    True if specified rows are removed and the integrity of the rows list is
    maintained; False if any specified rows are not removed, if any
    non-specified rows are missing, or if new rows have been added.
  """
  for row_id in ids:
    if not any(row for row in before if getattr(row, id_name) == row_id):
      raise ValueError(f"row ID {row_id} not present in before.")

  # Validate the removal and intactness of other rows
  for row in before:
    # If the row ID is in the list of removed row IDs
    if getattr(row, id_name) in ids:
      if row in after:
        return False
    elif row not in after:
      # Make sure we didn't remove other rows.
      return False

  # Check that no new unexpected rows have been added
  for row in after:
    if row not in before:
      return False

  return True


def validate_rows_addition_integrity(
    before: list[sqlite_schema_utils.RowType],
    after: list[sqlite_schema_utils.RowType],
    reference_rows: list[sqlite_schema_utils.RowType],
    compare_fields: list[str],
    free_form_fields: list[str] | None = None,
) -> bool:
  """Validates that specific rows have been added correctly without side effects.

  Checks that `reference_rows` are present in `after` and not in `before`, and
  that the rest of the rows in `before` remain unaltered in `after`. This
  validation ensures that no unrelated rows were added, removed, or changed in
  the process.

  Args:
    before: The state of the rows before the addition.
    after: The state of the rows after the attempted addition.
    reference_rows: A list of rows that are expected to be added.
    compare_fields: Which fields to use for comparison for each row.
    free_form_fields: Free-form, text fields where fuzzy matching will be used
      for comparison.

  Returns:
      bool: True if the rows were added correctly and other rows remained
      unaltered. False otherwise.
  """
  if not compare_fields:
    raise ValueError("compare_fields must not be empty.")
  if not free_form_fields:
    free_form_fields = []

  def db_row_matches_reference(
      reference_row: sqlite_schema_utils.RowType,
      row: sqlite_schema_utils.RowType,
  ) -> bool:
    for field in compare_fields:
      reference_value = getattr(reference_row, field)
      candidate_value = getattr(row, field)
      # Fuzzy match for text fields.
      if field in free_form_fields:
        if not fuzzy_match(reference_value, candidate_value):
          return False
      else:
        if reference_value != candidate_value:
          return False
    return True

  # Check if the added rows are present in the 'after' state
  for reference_row in reference_rows:
    if not any(db_row_matches_reference(reference_row, row) for row in after):
      logging.warning(
          "Expected row %s not found in the 'after' state.", reference_row
      )
      return False

  if len(after) != len(before) + len(reference_rows):
    logging.warning(
        "The length of after %i is not equal to the length of before %i +"
        " length of added rows %i",
        len(after),
        len(before),
        len(reference_rows),
    )
    return False

  # Validate that no other rows were altered or removed during the addition
  for row in before:
    if row not in after:
      logging.warning(
          "row %s from 'before' state missing or altered in the 'after' state.",
          row,
      )
      return False

  return True


def validate_event_removal_integrity(
    before: list[sqlite_schema_utils.CalendarEvent],
    after: list[sqlite_schema_utils.CalendarEvent],
    event_ids: list[int],
) -> bool:
  """Validates that events have been removed from the event list.

  See `sqlite_evaluators.validate_rows_removal_integrity` for details.

  Args:
    before: State of the events before removal, as a list of event tuples.
    after: State of the events after attempted removal, as a list of event
      tuples.
    event_ids: IDs of the events expected to be removed.

  Returns:
    True if specified events are removed and the integrity of the event list is
    maintained; False if any specified events are not removed, if any
    non-specified events are missing, or if new events have been added.
  """
  return validate_rows_removal_integrity(
      before, after, event_ids, 'id'
  )


def validate_event_addition_integrity(
    before: list[sqlite_schema_utils.CalendarEvent],
    after: list[sqlite_schema_utils.CalendarEvent],
    reference_events: list[sqlite_schema_utils.CalendarEvent],
    extras_compare: list[str] | None = None,
) -> bool:
  """Validates that specific events have been added correctly without side effects.

  By default, checks the following fields:
    - start_ts
    - end_ts
    - title  # Uses fuzzy match.
    - location  # Uses fuzzy match.
    - description  # Uses fuzzy match.

  Additional fields can be checked with `extras_compare`.

  Args:
      before: The state of the events before the addition.
      after: The state of the events after the attempted addition.
      reference_events: A list of events that are expected to be added.
      extras_compare: Additional fields to compare, if any.

  Returns:
      bool: True if the events were added correctly and other events remained
      unaltered. False otherwise.
  """

  # Default fields to compare
  compare_fields = [
      'start_ts',
      'end_ts',
      'title',
      'location',
  ]
  free_form_fields = ['title', 'location']
  if extras_compare:
    compare_fields += extras_compare
  return validate_rows_addition_integrity(
      before, after, reference_events, compare_fields, free_form_fields
  )







"""Debug evaluators for Simple Calendar Pro.

These evaluators verify calendar event operations (add/delete) by comparing
the before and after state of the calendar database.
"""

from android_world.env import interface
from android_world.task_evals.single.calendar import calendar_utils
from android_world.task_evals.utils import sqlite_utils


# ============================================================================
# 验证函数：可被多个任务类复用
# ============================================================================

def format_timestamp(ts: int | None) -> str:
  """将时间戳转换为可读的时间字符串。

  Args:
    ts: 时间戳（秒），如果为 None 返回 "Not specified"

  Returns:
    格式化的时间字符串，格式如 "2024-01-15 14:30:00"
  """
  if ts is None:
    return "Not specified"
  dt = datetime.fromtimestamp(ts, tz=timezone.utc)
  return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_current_events(env: interface.AsyncEnv) -> list[sqlite_schema_utils.CalendarEvent]:
  """获取当前日历事件列表。

  Args:
    env: Android 环境接口。

  Returns:
    当前日历事件列表。
  """
  return sqlite_utils.get_rows_from_remote_device(
      calendar_utils.EVENTS_TABLE,
      calendar_utils.DB_PATH,
      sqlite_schema_utils.CalendarEvent,
      env,
  )


CALENDAR_EVENT_PROMPT = """You are a calendar event validation assistant. Please determine whether the actual added calendar event meets the task requirements.

Task Requirements (Expected Event):
- Title: {expected_title}
- Location: {expected_location}

Actual Added Event:
- Title: {actual_title}
- Location: {actual_location}

Judgment Rules:
1. Title: Use semantic matching - expressions with the same meaning are acceptable
2. Location:
   - Use semantic matching if both have location
   - If one has location and the other doesn't, it is a failure

Note: Time fields have already been validated and match exactly.
"""


def validate_event_added(
    env: interface.AsyncEnv,
    goal: str,
    before_events: list[sqlite_schema_utils.CalendarEvent],
    expected_title: str,
    expected_start_ts: int | None = None,
    expected_end_ts: int | None = None,
    expected_location: str | None = None,
) -> bool:
  """验证单个日历事件是否被正确添加。

  验证逻辑：
  - 使用 LLM 判断事件是否正确添加
  - 只验证传入的参数，没传入的不做要求

  Args:
    env: Android 环境接口。
    goal: 任务目标，描述代理应该完成什么。
    before_events: 任务执行前的事件列表。
    expected_title: 期望的事件标题。
    expected_start_ts: 期望的开始时间戳（可选）。
    expected_end_ts: 期望的结束时间戳（可选）。
    expected_location: 期望的地点（可选）。

  Returns:
    True 如果验证通过，False 否则。
  """
  # 获取当前事件列表
  after_events = get_current_events(env)

  print(f"[DEBUG] Before events: {len(before_events)}")
  print(f"[DEBUG] After events: {len(after_events)}")

  # 打印实际添加的事件详情
  for i, event in enumerate(after_events):
    print(f"[DEBUG] After event {i}: title='{event.title}', start_ts={event.start_ts}, end_ts={event.end_ts}")
    print(f"[DEBUG]   start_datetime={event.start_datetime}, end_datetime={event.end_datetime}")

  # 打印期望的事件
  print(f"[DEBUG] Expected: title='{expected_title}', start_time={format_timestamp(expected_start_ts)}, end_time={format_timestamp(expected_end_ts)}")

  # 如果没有传入任何验证字段，直接返回 True
  if not expected_title:
    print("[DEBUG] No fields to validate, returning True")
    return True

  # 计算新增的事件（原来没有的）
  new_events = [e for e in after_events if e not in before_events]

  if not new_events:
    print("[DEBUG] No new events found, returning False")
    return False

  # 检查是否只添加了一个事件（验证数量正确性）
  if len(new_events) != 1:
    print(f"[DEBUG] Expected 1 new event, but found {len(new_events)}. Validation failed.")
    return False

  # 取第一个新增的事件进行对比
  actual_event = new_events[0]

  # 先判断时间字段是否相等，如果不相等直接返回 False，不调用 LLM
  if expected_start_ts is not None and actual_event.start_ts != expected_start_ts:
    print(f"[DEBUG] Start time mismatch: expected {format_timestamp(expected_start_ts)}, got {format_timestamp(actual_event.start_ts)}")
    return False
  if expected_end_ts is not None and actual_event.end_ts != expected_end_ts:
    print(f"[DEBUG] End time mismatch: expected {format_timestamp(expected_end_ts)}, got {format_timestamp(actual_event.end_ts)}")
    return False

  # 构建期望事件的数据字典（只包含传入的字段）
  expected_data = {"title": expected_title}
  if expected_start_ts is not None:
    expected_data["start_ts"] = expected_start_ts
  if expected_end_ts is not None:
    expected_data["end_ts"] = expected_end_ts
  if expected_location is not None:
    expected_data["location"] = expected_location


  # 构建 prompt，只验证 title 和 location
  prompt = CALENDAR_EVENT_PROMPT.format(
      expected_title=expected_title,
      expected_start_ts=format_timestamp(expected_start_ts),
      expected_end_ts=format_timestamp(expected_end_ts),
      expected_location=expected_location if expected_location is not None else "Not specified",
      actual_title=actual_event.title if actual_event.title is not None else "Not specified",
      actual_start_ts=format_timestamp(actual_event.start_ts),
      actual_end_ts=format_timestamp(actual_event.end_ts),
      actual_location=actual_event.location if actual_event.location is not None else "Not specified",
  )

  print(f"[DEBUG] Calling LLM to validate event...")
  is_match, explanation = llm_as_judge.llm_judge(goal, prompt)
  print(f"[DEBUG] LLM judgment: {is_match}, Explanation: {explanation}")

  return is_match


def validate_event_deleted(
    env: interface.AsyncEnv,
    before_events: list[sqlite_schema_utils.CalendarEvent],
    event_title: str,
) -> bool:
  """验证单个日历事件是否被正确删除。

  Args:
    env: Android 环境接口。
    before_events: 任务执行前的事件列表。
    event_title: 要删除的事件标题。

  Returns:
    True 如果验证通过，False 否则。
  """
  # 获取当前事件列表
  after_events = get_current_events(env)

  print(f"[DEBUG] Before events: {len(before_events)}")
  print(f"[DEBUG] After events: {len(after_events)}")

  # 查找要删除的事件ID
  event_ids_to_delete = []
  for event in before_events:
    if event.title == event_title:
      event_ids_to_delete.append(event.id)

  if not event_ids_to_delete:
    print(f"[DEBUG] No event found with title: {event_title}")
    return False

  print(f"[DEBUG] Events to delete: {event_ids_to_delete}")

  # 验证事件是否被删除
  result = validate_event_removal_integrity(
      before_events,
      after_events,
      event_ids_to_delete,
  )

  print(f"[DEBUG] Event deletion validated: {result}")
  return result


def validate_events_deleted(
    env: interface.AsyncEnv,
    before_events: list[sqlite_schema_utils.CalendarEvent],
    event_titles: list[str],
) -> bool:
  """验证多个日历事件是否被正确删除。

  Args:
    env: Android 环境接口。
    before_events: 任务执行前的事件列表。
    event_titles: 要删除的事件标题列表。

  Returns:
    True 如果验证通过，False 否则。
  """
  # 获取当前事件列表
  after_events = get_current_events(env)

  print(f"[DEBUG] Before events: {len(before_events)}")
  print(f"[DEBUG] After events: {len(after_events)}")

  # 查找要删除的事件ID
  event_ids_to_delete = []
  for event in before_events:
    if event.title in event_titles:
      event_ids_to_delete.append(event.id)

  if not event_ids_to_delete:
    print(f"[DEBUG] No events found with titles: {event_titles}")
    return False

  print(f"[DEBUG] Events to delete: {event_ids_to_delete}")

  # 验证事件是否被删除
  result = validate_event_removal_integrity(
      before_events,
      after_events,
      event_ids_to_delete,
  )

  print(f"[DEBUG] Multiple events deletion validated: {result}")
  return result


def validate_event_time_modified(
    env: interface.AsyncEnv,
    before_events: list[sqlite_schema_utils.CalendarEvent],
    expected_title: str,
    expected_start_ts: int | None = None,
    expected_end_ts: int | None = None,
) -> bool:
  """验证日历事件的时间是否被正确修改。

  验证逻辑：
  - 查找与 expected_title 匹配的事件
  - 验证其开始时间和/或结束时间是否被正确修改

  Args:
    env: Android 环境接口。
    goal: 任务目标，描述代理应该完成什么。
    before_events: 任务执行前的事件列表。
    expected_title: 期望被修改的事件标题。
    expected_start_ts: 期望的新开始时间戳（可选）。
    expected_end_ts: 期望的新结束时间戳（可选）。

  Returns:
    True 如果验证通过，False 否则。
  """
  # 获取当前事件列表
  after_events = get_current_events(env)

  print(f"[DEBUG] Before events: {len(before_events)}")
  print(f"[DEBUG] After events: {len(after_events)}")

  # 查找被修改的事件（通过 title 匹配）
  modified_event = None
  original_event = None

  for before_event in before_events:
    if fuzzy_match(before_event.title, expected_title):
      original_event = before_event
      # 查找修改后对应的事件
      for after_event in after_events:
        if fuzzy_match(after_event.title, expected_title):
          modified_event = after_event
          break
      break

  if not original_event:
    print(f"[DEBUG] No event found with title: {expected_title}")
    return False

  if not modified_event:
    print(f"[DEBUG] Event with title '{expected_title}' was deleted")
    return False

  for i, event in enumerate(after_events):
    print(f"[DEBUG] After event {i}: title='{event.title}', start_ts={event.start_ts}, end_ts={event.end_ts}")
    print(f"[DEBUG]   start_datetime={event.start_datetime}, end_datetime={event.end_datetime}")

  # 打印期望的事件
  print(f"[DEBUG] Expected: title='{expected_title}', start_time={format_timestamp(expected_start_ts)}, end_time={format_timestamp(expected_end_ts)}")
  print(f"[DEBUG] Original event: start={format_timestamp(original_event.start_ts)}, end={format_timestamp(original_event.end_ts)}")
  print(f"[DEBUG] Modified event: start={format_timestamp(modified_event.start_ts)}, end={format_timestamp(modified_event.end_ts)}")

  
  start_changed = expected_start_ts is not None and modified_event.start_ts == expected_start_ts
  end_changed = expected_end_ts is not None and modified_event.end_ts == expected_end_ts

  # 如果两个时间都指定了，必须都匹配；如果只指定一个，匹配一个即可
  if expected_start_ts is not None and expected_end_ts is not None:
    result = start_changed and end_changed
  elif expected_start_ts is not None:
    result = start_changed
  elif expected_end_ts is not None:
    result = end_changed
  else:
    print("[DEBUG] No time validation parameters provided")
    return False

  print(f"[DEBUG] Time modification validation result: {result}")
  return result