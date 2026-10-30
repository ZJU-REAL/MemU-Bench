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

"""Debug evaluators for Simple Calendar Pro.

These evaluators verify calendar event operations (add/delete) by comparing
the before and after state of the calendar database.
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.common_validators import sqlite_validators
from android_world.task_evals.custom_validators import calendar
from android_world.task_evals.single.calendar import calendar_utils
from android_world.task_evals.utils import sqlite_schema_utils
from android_world.task_evals.utils import sqlite_utils





# ============================================================================
# 任务类
# ============================================================================
class DebugCalendarAddEvent(fixed_task_eval.TaskEval):
  """固定任务：验证日历事件是否被添加。

  Agent 需要在 Simple Calendar Pro 中添加一个指定的日程事件。
  验证方式：比较任务执行前后的日历数据库状态。
  """

  complexity = 1.0

  # 固定的事件参数
  _EVENT_TITLE = "Team Meeting"
  _START_TS = 1792490400  # 2026-10-20 10:00:00 UTC
  _END_TS = 1792494000    # 2026-10-20 11:00:00 UTC (60 minutes later)
  _LOCATION = ""
  _DESCRIPTION = ""

  @property
  def goal(self) -> str:
    """任务目标。"""
    return "In Simple Calendar Pro, add a calendar event titled 'Team Meeting' on 2026-10-20 at 10:00, lasting 60 minutes"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空日历数据库，存储初始状态。"""
    print("[DEBUG] Clearing calendar database...")
    calendar_utils.clear_calendar_db(env)
    print("[DEBUG] Calendar database cleared")
    self._before_events = calendar.get_current_events(env)
    print(f"[DEBUG] Stored before state: {len(self._before_events)} events")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_events'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = calendar.validate_event_added(
        env=env,
        before_events=self._before_events,
        expected_title=self._EVENT_TITLE,
        expected_start_ts=self._START_TS,
        expected_end_ts=self._END_TS,
        expected_location=self._LOCATION,
        expected_description=self._DESCRIPTION,
    )
    return 1.0 if result else 0.0

class DebugCalendarDeleteEvent(fixed_task_eval.TaskEval):
  """固定任务：验证日历事件是否被删除。

  Agent 需要在 Simple Calendar Pro 中删除指定的日程事件。
  验证方式：比较任务执行前后的日历数据库状态。
  """

  complexity = 1.0

  # 固定的事件标题
  _EVENT_TITLE = "Team Meeting"

  # 要预先添加的事件（供删除）
  _PRESET_EVENT = sqlite_schema_utils.CalendarEvent(
      start_ts=1792490400,  # 2026-10-20 10:00:00 UTC
      end_ts=1792494000,    # 2026-10-20 11:00:00 UTC (60 minutes later)
      title="Team Meeting",
      location="",
      description="",
  )

  @property
  def goal(self) -> str:
    """任务目标。"""
    return "In Simple Calendar Pro, delete the calendar event titled 'Team Meeting'"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空日历数据库，添加预设事件，存储初始状态。"""
    print("[DEBUG] Clearing calendar database...")
    calendar_utils.clear_calendar_db(env)
    print("[DEBUG] Calendar database cleared")

    # 添加预设事件
    print(f"[DEBUG] Adding preset event: {self._PRESET_EVENT.title}")
    calendar_utils.add_events([self._PRESET_EVENT], env)
    print("[DEBUG] Preset event added")

    self.set_before_state(env)

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_events'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = calendar.validate_event_deleted(
        env=env,
        before_events=self._before_events,
        event_title=self._EVENT_TITLE,
    )
    return 1.0 if result else 0.0

  def set_before_state(self, env: interface.AsyncEnv) -> None:
    """存储任务执行前的日历状态。

    Args:
      env: Android 环境接口。
    """
    self._before_events = sqlite_utils.get_rows_from_remote_device(
        calendar_utils.EVENTS_TABLE,
        calendar_utils.DB_PATH,
        sqlite_schema_utils.CalendarEvent,
        env,
    )
    print(f"[DEBUG] Stored before state: {len(self._before_events)} events")


class DebugCalendarAddMultipleEvents(fixed_task_eval.TaskEval):
  """固定任务：验证多个日历事件是否被添加。

  Agent 需要在 Simple Calendar Pro 中添加多个日程事件。
  验证方式：比较任务执行前后的日历数据库状态。
  """

  complexity = 1.5

  # 固定的事件参数
  _EVENTS = [
      {
          "title": "Morning Standup",
          "start_ts": 1792573200,  # 实际添加的时间戳
          "end_ts": 1792575000,
          "location": "Meeting Room A",
          "description": "Daily standup meeting",
      },
      {
          "title": "Project Review",
          "start_ts": 1792591200,  # 实际添加的时间戳
          "end_ts": 1792596600,
          "location": "Conference Room",
          "description": "Quarterly project review",
      },
  ]

  @property
  def goal(self) -> str:
    """任务目标。"""
    return "In Simple Calendar Pro, add two calendar events: 'Morning Standup' on 2026-10-21 at 09:00 for 30 minutes, and 'Project Review' on 2026-10-21 at 14:00 for 90 minutes"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空日历数据库，存储初始状态。"""
    print("[DEBUG] Clearing calendar database...")
    calendar_utils.clear_calendar_db(env)
    print("[DEBUG] Calendar database cleared")
    self.set_before_state(env)

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_events'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = calendar.validate_events_added(
        env=env,
        before_events=self._before_events,
        expected_events=self._EVENTS,
    )
    return 1.0 if result else 0.0

  def set_before_state(self, env: interface.AsyncEnv) -> None:
    """存储任务执行前的日历状态。

    Args:
      env: Android 环境接口。
    """
    self._before_events = sqlite_utils.get_rows_from_remote_device(
        calendar_utils.EVENTS_TABLE,
        calendar_utils.DB_PATH,
        sqlite_schema_utils.CalendarEvent,
        env,
    )
    print(f"[DEBUG] Stored before state: {len(self._before_events)} events")


class DebugCalendarDeleteMultipleEvents(fixed_task_eval.TaskEval):
  """固定任务：验证多个日历事件是否被删除。

  Agent 需要在 Simple Calendar Pro 中删除多个日程事件。
  验证方式：比较任务执行前后的日历数据库状态。
  """

  complexity = 1.5

  # 固定的事件标题列表（按标题删除）
  _EVENT_TITLES = ["Morning Standup", "Project Review"]

  # 要预先添加的事件（供删除）
  _PRESET_EVENTS = [
      sqlite_schema_utils.CalendarEvent(
          start_ts=1792576800,  # 2026-10-21 09:00:00 UTC
          end_ts=1792578600,    # 2026-10-21 09:30:00 UTC (30 minutes)
          title="Morning Standup",
          location="Meeting Room A",
          description="Daily standup meeting",
      ),
      sqlite_schema_utils.CalendarEvent(
          start_ts=1792594800,  # 2026-10-21 14:00:00 UTC
          end_ts=1792600200,    # 2026-10-21 15:30:00 UTC (90 minutes)
          title="Project Review",
          location="Conference Room",
          description="Quarterly project review",
      ),
  ]

  @property
  def goal(self) -> str:
    """任务目标。"""
    return "In Simple Calendar Pro, delete all calendar events on 2026-10-21"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空日历数据库，添加预设事件，存储初始状态。"""
    print("[DEBUG] Clearing calendar database...")
    calendar_utils.clear_calendar_db(env)
    print("[DEBUG] Calendar database cleared")

    # 添加预设事件
    print(f"[DEBUG] Adding {len(self._PRESET_EVENTS)} preset events...")
    calendar_utils.add_events(self._PRESET_EVENTS, env)
    print("[DEBUG] Preset events added")

    self.set_before_state(env)

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_events'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = calendar.validate_events_deleted(
        env=env,
        before_events=self._before_events,
        event_titles=self._EVENT_TITLES,
    )
    return 1.0 if result else 0.0

  def set_before_state(self, env: interface.AsyncEnv) -> None:
    """存储任务执行前的日历状态。

    Args:
      env: Android 环境接口。
    """
    self._before_events = sqlite_utils.get_rows_from_remote_device(
        calendar_utils.EVENTS_TABLE,
        calendar_utils.DB_PATH,
        sqlite_schema_utils.CalendarEvent,
        env,
    )
    print(f"[DEBUG] Stored before state: {len(self._before_events)} events")