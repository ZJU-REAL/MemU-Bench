

"""Tasks for the clock app."""

import random
from typing import Optional
from absl import logging
from android_world.env import adb_utils
from android_world.env import interface
from android_world.env import representation_utils
from android_world.task_evals import task_eval
import time


# ============================================================================
# 闹钟验证函数 (UI 验证方式)
# ============================================================================


def _parse_time_from_text(text: str) -> list[tuple[int, int]]:
    """从文本中解析所有时间（小时:分钟）。

    支持格式：7:30, 07:30, 7:30 AM, 07:30PM 等。

    Args:
        text: 待解析的文本。

    Returns:
        解析出的 (hour, minute) 列表，24小时制。
    """
    import re
    results = []
    # 匹配 h:mm 或 hh:mm，可选后跟 AM/PM
    pattern = r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)?'
    for match in re.finditer(pattern, text):
        h = int(match.group(1))
        m = int(match.group(2))
        ampm = match.group(3)
        if ampm:
            ampm = ampm.upper()
            if ampm == 'AM':
                if h == 12:
                    h = 0
            elif ampm == 'PM':
                if h != 12:
                    h += 12
        results.append((h, m))
    return results


def _find_alarm_in_ui_elements(
    ui_elements: list[representation_utils.UIElement],
    hour: int,
    minute: int,
    fuzzy_minutes: Optional[int] = None,
) -> tuple[bool, list[str]]:
    """在 UI 元素列表中查找指定时间的闹钟。

    Args:
        ui_elements: UI 元素列表。
        hour: 小时。
        minute: 分钟。
        fuzzy_minutes: 模糊匹配阈值（分钟），如果传入则时间差距小于此值也算匹配。

    Returns:
        (是否找到, 所有检测到的文本列表用于调试)
    """
    # 常见的时间显示格式（24小时制和12小时制）
    time_patterns = [
        f"{hour}:{minute:02d}",           # 7:30
        f"{hour:02d}:{minute:02d}",       # 07:30
    ]
    # 12小时制格式
    hour_12 = hour % 12 if hour % 12 != 0 else 12
    am_pm = "AM" if hour < 12 else "PM"
    time_patterns.extend([
        f"{hour_12}:{minute:02d}",           # 7:30
        f"{hour_12}:{minute:02d} {am_pm}",    # 7:30 AM/PM
        f"{hour_12}:{minute:02d}{am_pm.lower()}",  # 7:30am/pm
    ])

    # print(f"[DEBUG] Searching for alarm patterns: {time_patterns}")
    # if fuzzy_minutes is not None:
    #     print(f"[DEBUG] Fuzzy matching enabled, tolerance: {fuzzy_minutes} minutes")

    debug_texts = []
    for i, element in enumerate(ui_elements):
        text = element.text or ""
        content_desc = element.content_description or ""
        debug_texts.append(f"[{i}] text='{text}', desc='{content_desc}'")

        # 精确匹配
        for pattern in time_patterns:
            if pattern in text or pattern in content_desc:
                return True, debug_texts

        # 模糊匹配：解析文本中的时间，检查与期望时间的差距
        if fuzzy_minutes is not None:
            expected_total = hour * 60 + minute
            for source in [text, content_desc]:
                for parsed_h, parsed_m in _parse_time_from_text(source):
                    parsed_total = parsed_h * 60 + parsed_m
                    diff = abs(parsed_total - expected_total)
                    if diff < fuzzy_minutes:
                        return True, debug_texts

    return False, debug_texts


def _find_alarm_in_ui(
    env: interface.AsyncEnv,
    hour: int,
    minute: int,
    fuzzy_minutes: Optional[int] = None,
) -> tuple[bool, list[str]]:
    """在 UI 中查找指定时间的闹钟。

    Args:
        env: Android 环境接口。
        hour: 小时。
        minute: 分钟。
        fuzzy_minutes: 模糊匹配阈值（分钟），如果传入则时间差距小于此值也算匹配。

    Returns:
        (是否找到, 所有检测到的文本列表用于调试)
    """
    state = env.get_state()
    return _find_alarm_in_ui_elements(state.ui_elements, hour, minute, fuzzy_minutes)


def _is_alarm_enabled(
    env: interface.AsyncEnv,
    hour: int,
    minute: int,
) -> tuple[bool, bool, list[str]]:
    """检查闹钟是否启用。

    Args:
        env: Android 环境接口。
        hour: 小时。
        minute: 分钟。

    Returns:
        (是否找到, 是否启用, 调试文本列表)
        启用的判断依据是 UI 中是否显示开关为开启状态或没有禁用标识
    """
    state = env.get_state()
    ui_elements = state.ui_elements

    # 先找到闹钟所在区域
    time_patterns = [
        f"{hour}:{minute:02d}",
        f"{hour:02d}:{minute:02d}",
    ]
    hour_12 = hour % 12 if hour % 12 != 0 else 12
    am_pm = "AM" if hour < 12 else "PM"
    time_patterns.extend([
        f"{hour_12}:{minute:02d}",
        f"{hour_12}:{minute:02d} {am_pm}",
    ])

    debug_texts = []
    alarm_found = False
    alarm_enabled = False

    # 查找闹钟时间附近是否有启用开关或其他状态标识
    for i, element in enumerate(ui_elements):
        text = element.text or ""
        content_desc = element.content_description or ""
        debug_texts.append(f"[{i}] text='{text}', desc='{content_desc}', class='{element.class_name}'")

        # 检查是否找到时间
        for pattern in time_patterns:
            if pattern in text or pattern in content_desc:
                alarm_found = True
                # 检查附近元素是否有开关状态
                # Google Clock 通常用 Switch 或 Checkbox 显示状态
                # 或者通过文字如 "On"/"Off" 或图标表示
                for j in range(max(0, i-3), min(len(ui_elements), i+4)):
                    nearby_text = ui_elements[j].text or ""
                    nearby_desc = ui_elements[j].content_description or ""
                    nearby_class = ui_elements[j].class_name or ""

                    # 检查开关类控件
                    if "switch" in nearby_class.lower():
                        # Switch 控件通常 checked 状态表示启用
                        alarm_enabled = True  # 找到 switch 默认认为可能启用
                    if "On" in nearby_text or "ON" in nearby_text:
                        alarm_enabled = True
                    if "checked" in nearby_desc.lower() or "on" in nearby_desc.lower():
                        alarm_enabled = True

                break

    return alarm_found, alarm_enabled, debug_texts


def clear_alarms(env: interface.AsyncEnv) -> None:
    """清除所有闹钟（通过清除应用数据）。

    Args:
        env: Android 环境接口。
    """
    _close_clock_app(env)
    print("[DEBUG] All alarms cleared via app data reset")


def _check_text_in_ui_elements(
    ui_elements: list,
    text: str,
    fuzzy_match: bool = True,
    check_description: bool = False,
) -> bool:
    """Check if a specific text appears in any UI element.

    Args:
        ui_elements: List of UI elements to search.
        text: The text to look for.
        fuzzy_match: If True, uses case-insensitive partial matching.
        check_description: If True, also check content_description field.
            Default is False for required texts validation.

    Returns:
        True if the text is found, False otherwise.
    """
    text_lower = text.lower().strip()

    for element in ui_elements:
        # Check text field
        if element.text:
            if fuzzy_match:
                if text_lower in element.text.lower():
                    return True
            else:
                if element.text.strip() == text:
                    return True

        # Check content_description field only if requested
        if check_description and element.content_description:
            if fuzzy_match:
                if text_lower in element.content_description.lower():
                    return True
            else:
                if element.content_description.strip() == text:
                    return True

    return False


def validate_alarm_added(
    env: interface.AsyncEnv,
    expected_hour: int,
    expected_minute: int,
    fuzzy_minutes: Optional[int] = None,
    required_texts: Optional[list[str]] = None,
) -> bool:
    """验证闹钟是否被正确添加（UI 验证方式）。

    Args:
        env: Android 环境接口。
        expected_hour: 期望的小时（0-23）。
        expected_minute: 期望的分钟（0-59）。
        fuzzy_minutes: 模糊匹配阈值（分钟），如果传入则闹钟时间与期望时间
            差距小于此值也算匹配。例如 fuzzy_minutes=5 表示差5分钟以内都算正确。
        required_texts: 可选列表，包含必须在 UI 中出现的额外文本
            用于确认闹钟设置完整（如 ["Sunday", "Repeat"]）。

    Returns:
        True 如果验证通过，False 否则。
    """
    from android_world.env import adb_utils

    # 等待一下让UI稳定
    time.sleep(1.0)

    # 使用uiautomator dump获取UI（绕过gRPC缓存）
    try:
        xml_dump = adb_utils.uiautomator_dump(env.controller)
        ui_elements = representation_utils.xml_dump_to_ui_elements(xml_dump)
    except Exception as e:
        state = env.get_state(wait_to_stabilize=False)
        ui_elements = state.ui_elements

    # 通过 UI 查找闹钟
    found, debug_texts = _find_alarm_in_ui_elements(
        ui_elements, expected_hour, expected_minute, fuzzy_minutes
    )

    if not found:
        # 未找到，打印调试信息
        # print(f"[DEBUG] Alarm not found in UI. Detected elements:")
        # for text in debug_texts[:20]:  # 限制输出数量
        #     print(f"  {text}")
        # print(f"[DEBUG] Alarm addition validated: False")
        return False

    # 检查必需的额外文本
    if required_texts:
        print(f"[DEBUG] Checking required texts: {required_texts}")
        print(f"[DEBUG] Total UI elements to search: {len(ui_elements)}")

        # 打印所有 UI 元素用于调试
        print(f"[DEBUG] All UI elements:")
        for i, element in enumerate(ui_elements):
            text = element.text or ""
            desc = element.content_description or ""
            if text or desc:
                print(f"[DEBUG]   [{i}] text='{text}', desc='{desc}'")

        for required_text in required_texts:
            # Required texts only match against text field, not content_description
            found_text = _check_text_in_ui_elements(
                ui_elements, required_text, fuzzy_match=True, check_description=False
            )
            print(f"[DEBUG] Searching for '{required_text}' in text fields: {'FOUND' if found_text else 'NOT FOUND'}")
            if not found_text:
                print(f"[DEBUG] Required text '{required_text}' not found in UI text elements")
                return False
            print(f"[DEBUG] Required text '{required_text}' found")

    print(f"[DEBUG] Alarm addition validated: True")
    return True


def validate_alarm_deleted(
    env: interface.AsyncEnv,
    alarm_hour: int,
    alarm_minute: int,
    required_texts: Optional[list[str]] = None,
) -> bool:
    """验证闹钟是否被正确删除（UI 验证方式）。

    Args:
        env: Android 环境接口。
        alarm_hour: 要删除的闹钟小时。
        alarm_minute: 要删除的闹钟分钟。
        required_texts: 可选列表，包含必须在 UI 中出现的额外文本
            用于确认其他闹钟未被误删（如 ["8:00", "14:30"]）。

    Returns:
        True 如果验证通过，False 否则。
    """
    # print(f"[DEBUG] Looking for alarm to delete: {alarm_hour:02d}:{alarm_minute:02d}")

    from android_world.env import adb_utils

    # 打印当前activity
    # current_activity = adb_utils.get_current_activity(env.controller)[0]
    # print(f"[DEBUG] Current activity: {current_activity}")

    # 等待一下让UI稳定
    time.sleep(1.0)

    # 使用uiautomator dump获取UI（绕过gRPC缓存）
    # print(f"[DEBUG] Getting UI via uiautomator dump...")
    try:
        xml_dump = adb_utils.uiautomator_dump(env.controller)
        ui_elements = representation_utils.xml_dump_to_ui_elements(xml_dump)
        # print(f"[DEBUG] Got {len(ui_elements)} elements from uiautomator")
    except Exception as e:
        # print(f"[DEBUG] uiautomator failed: {e}, falling back to env.get_state()")
        state = env.get_state(wait_to_stabilize=False)
        ui_elements = state.ui_elements

    # 通过 UI 查找闹钟
    found, debug_texts = _find_alarm_in_ui_elements(ui_elements, alarm_hour, alarm_minute)

    # 打印所有 UI 元素用于调试
    # print(f"[DEBUG] UI elements found: {len(debug_texts)}")
    # for text in debug_texts[:30]:
    #     print(f"[DEBUG] {text}")

    if found:
        # print(f"[DEBUG] Alarm still exists in UI")
        return False

    # 检查必需的额外文本（确认其他闹钟未被误删）
    if required_texts:
        print(f"[DEBUG] Checking required texts after deletion: {required_texts}")
        print(f"[DEBUG] Total UI elements to search: {len(ui_elements)}")

        print(f"[DEBUG] All UI elements:")
        for i, element in enumerate(ui_elements):
            text = element.text or ""
            desc = element.content_description or ""
            if text or desc:
                print(f"[DEBUG]   [{i}] text='{text}', desc='{desc}'")

        for required_text in required_texts:
            found_text = _check_text_in_ui_elements(
                ui_elements, required_text, fuzzy_match=True, check_description=False
            )
            print(f"[DEBUG] Searching for '{required_text}' in text fields: {'FOUND' if found_text else 'NOT FOUND'}")
            if not found_text:
                print(f"[DEBUG] Required text '{required_text}' not found in UI, other alarm may have been deleted")
                return False
            print(f"[DEBUG] Required text '{required_text}' found")

    # print(f"[DEBUG] Alarm deletion validated: True (alarm not found in UI)")
    return True


def validate_alarm_enabled(
    env: interface.AsyncEnv,
    alarm_hour: int,
    alarm_minute: int,
    expected_enabled: bool = True,
) -> bool:
    """验证闹钟是否被启用/禁用（UI 验证方式）。

    Args:
        env: Android 环境接口。
        alarm_hour: 闹钟小时。
        alarm_minute: 闹钟分钟。
        expected_enabled: 期望的启用状态。

    Returns:
        True 如果验证通过，False 否则。
    """
    print(f"[DEBUG] Looking for alarm at {alarm_hour:02d}:{alarm_minute:02d}")
    print(f"[DEBUG] Expected enabled: {expected_enabled}")

    # 通过 UI 检查闹钟状态
    found, is_enabled, debug_texts = _is_alarm_enabled(env, alarm_hour, alarm_minute)

    if not found:
        print(f"[DEBUG] Alarm not found in UI")
        return False

    print(f"[DEBUG] Found alarm, detected enabled={is_enabled}")
    return is_enabled == expected_enabled


def validate_alarm_time_changed(
    env: interface.AsyncEnv,
    old_hour: int,
    old_minute: int,
    new_hour: int,
    new_minute: int,
) -> bool:
    """验证闹钟时间是否被修改（UI 验证方式）。

    Args:
        env: Android 环境接口。
        old_hour: 原来的小时。
        old_minute: 原来的分钟。
        new_hour: 新的小时。
        new_minute: 新的分钟。

    Returns:
        True 如果验证通过，False 否则。
    """
    print(f"[DEBUG] Looking for time change from {old_hour:02d}:{old_minute:02d} to {new_hour:02d}:{new_minute:02d}")

    # 检查旧时间是否不存在
    old_found, _ = _find_alarm_in_ui(env, old_hour, old_minute)
    if old_found:
        print(f"[DEBUG] Old alarm time {old_hour:02d}:{old_minute:02d} still exists")
        return False

    # 检查新时间是否存在
    new_found, debug_texts = _find_alarm_in_ui(env, new_hour, new_minute)
    if new_found:
        print(f"[DEBUG] Alarm time changed successfully")
        return True

    print(f"[DEBUG] New alarm time {new_hour:02d}:{new_minute:02d} not found")
    return False


def _is_stopwatch_running(
    ui_elements: list[representation_utils.UIElement],
    current_activity: str,
) -> bool:
  """Checks if current screen is stopwatch running."""
  if "DeskClock" not in current_activity:
    return False
  pause_present = False
  lap_present = False

  for element in ui_elements:
    if element.content_description == "Pause":
      pause_present = True
    elif element.content_description == "Lap":
      lap_present = True
  return pause_present and lap_present


def _is_stopwatch_paused(
    ui_elements: list[representation_utils.UIElement],
    current_activity: str,
) -> bool:
  """Checks if current screen is stopwatch paused."""
  if "DeskClock" not in current_activity:
    return False
  start_present = False
  n_stopwatch = 0

  for element in ui_elements:
    if element.content_description == "Start":
      start_present = True
    elif (
        element.content_description == "Stopwatch"
        or element.text == "Stopwatch"
    ):
      n_stopwatch += 1
  logging.info("Start present: %s", start_present)
  logging.info("Stopwatch: %d", n_stopwatch)
  return start_present and n_stopwatch >= 2


def _is_timer_set(
    ui_elements: list[representation_utils.UIElement],
    current_activity: str,
    *,
    hours: int,
    minutes: int,
    seconds: int,
) -> bool:
  """Determines if a timer is set.

  Args:
    ui_elements: A list of UI elements representing the interface components
      within the "DeskClock" activity.
    current_activity: The name of the current activity within the UI.
    hours: The number of hours to check for in the timer.
    minutes: The number of minutes to check for in the timer.
    seconds: The number of seconds to check for in the timer.

  Returns:
    True if the timer is set with the specified hours, minutes, and seconds
      within the "DeskClock" activity; False otherwise.
  """
  if "DeskClock" not in current_activity:
    return False
  text_format = f"{hours:02d}h {minutes:02d}m {seconds:02d}s"
  content_desc_format = f"{hours} hours, {minutes} minutes, {seconds} seconds"

  for element in ui_elements:
    if (
        element.text == text_format
        or element.content_description == content_desc_format
    ):
      return True

  return False


def _close_clock_app(env: interface.AsyncEnv):
  """Closes the clock app."""
  adb_utils.clear_app_data(
      adb_utils.extract_package_name(adb_utils.get_adb_activity("clock")),
      env.controller,
  )


def _open_clock_app(env: interface.AsyncEnv):
  """Opens the clock app."""
  from android_world.env import json_action
  open_action = json_action.JSONAction(action_type='open_app', app_name='clock')
  env.execute_action(open_action)



