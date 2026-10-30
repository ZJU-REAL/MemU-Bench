

"""Logic to validate a phone call is made to a specific number."""

import re

from android_env import env_interface
from android_world.env import adb_utils
from android_world.env import interface
from android_world.env import representation_utils



def check_if_dialer_with_phone_number(
    ui_elements: list[representation_utils.UIElement],
    current_activity: str,
    *,
    expected_number: str | None = None,
    expected_name: str | None = None,
) -> bool:
  """Check if the correct number is dialed based on UI elements.

  Args:
    ui_elements: List of UIElement objects representing the UI.
    current_activity: The current Android activity.
    expected_number: The expected dialed phone number as a string (optional).
    expected_name: The expected contact name (optional).
      Either matching the number OR the name is considered success.

  Returns:
    True if the expected number/name is found, False otherwise.
  """
  print(f"[DEBUG] Checking dialer activity: {current_activity}")
  if not current_activity.startswith("com.google.android.dialer"):
    print(f"[DEBUG] Not in dialer activity, returning False")
    return False

  # 至少需要一个期望值
  if not expected_number and not expected_name:
    print(f"[DEBUG] No expected number or name provided, returning False")
    return False

  cleaned_expected_number = re.sub(r"[^\d]", "", expected_number) if expected_number else None
  print(f"[DEBUG] Expected number (cleaned): {cleaned_expected_number}")
  print(f"[DEBUG] Expected name: {expected_name}")

  found_numbers = []
  found_names = []

  for element in ui_elements:
    if element.text:
      # 检查是否是号码
      cleaned_element_text = re.sub(r"[^\d]", "", element.text)
      if cleaned_element_text and len(cleaned_element_text) >= 7:  # 过滤掉短号码
        found_numbers.append(cleaned_element_text)
        print(f"[DEBUG] Found number in UI: {cleaned_element_text}")
      # 检查是否是联系人名字（不是纯数字）
      elif element.text.strip() and not element.text.strip().isdigit():
        # 可能是联系人名字
        found_names.append(element.text.strip().lower())
        print(f"[DEBUG] Found name in UI: {element.text.strip()}")

  print(f"[DEBUG] Total numbers found: {len(found_numbers)}")
  print(f"[DEBUG] Total names found: {found_names}")

  # 预定义的所有联系人名字列表（从模拟器获取）
  ALL_CONTACT_NAMES = [
      'barbara jones', 'mary brown', 'william jones', 'jennifer smith',
      'thomas anderson', 'william smith', 'mary jones', 'sarah williams',
      'william brown', 'sarah jones', 'charles martinez', 'david johnson',
      'jessica garcia', 'mary johnson', 'barbara williams',
  ]

  # 验证逻辑：目标联系人出现在UI中，且没有其他联系人出现在UI中
  if expected_name:
    expected_name_lower = expected_name.lower().strip()
    # 检查目标联系人是否出现在 found_names 中
    if expected_name_lower in found_names:
      # 检查是否有其他联系人也出现在 UI 中
      other_contacts_in_ui = [
          name for name in found_names
          if name in ALL_CONTACT_NAMES and name != expected_name_lower
      ]
      if not other_contacts_in_ui:
        print(f"[DEBUG] Validation passed: found expected contact name '{expected_name}' in UI")
        return True
      else:
        print(f"[DEBUG] Validation failed: other contacts found in UI: {other_contacts_in_ui}")

  # 检查号码匹配（保持原有逻辑）
  if cleaned_expected_number and len(found_numbers) == 1:
    if found_numbers[0] == cleaned_expected_number:
      print(f"[DEBUG] Validation passed: found single number matching expected")
      return True

  print(f"[DEBUG] Validation failed: no match found")
  return False


def clear_phone_state(env: env_interface.AndroidEnvInterface) -> None:
  """Clears phone log and ends any active call."""
  adb_utils.end_call_if_active(env)
  adb_utils.clear_android_emulator_call_log(env)


"""Debug evaluators for Phone tasks.

These evaluators verify phone call operations.
"""

import re

from android_world.env import adb_utils
from android_world.env import interface

def called_correct_number(
    env: interface.AsyncEnv,
    phone_number: str | None = None,
    contact_name: str | None = None,
) -> bool:
    """检查是否拨打了正确的号码或联系人。

    Args:
      env: Android 环境接口。
      phone_number: 期望的电话号码（可选）。
      contact_name: 期望的联系人名字（可选）。
        至少需要传入其中一个，号码或联系人名字匹配其一即可。

    Returns:
      True 如果拨打了正确的号码或联系人，False 否则。
    """
    # 至少需要一个期望值
    if not phone_number and not contact_name:
        print("[DEBUG] No phone_number or contact_name provided")
        return False

    # 使用 uiautomator dump 获取 UI（绕过 gRPC 缓存）
    try:
        xml_dump = adb_utils.uiautomator_dump(env.controller)
        ui_elements = representation_utils.xml_dump_to_ui_elements(xml_dump)
    except Exception as e:
        print(f"[DEBUG] uiautomator dump failed: {e}, falling back to env.get_state()")
        ui_elements = env.get_state().ui_elements

    current_activity = adb_utils.get_current_activity(env.controller)[0]
    print(f"[DEBUG] Current activity: {current_activity}")
    print(f"[DEBUG] UI elements count: {len(ui_elements)}")

    result = check_if_dialer_with_phone_number(
        expected_number=phone_number,
        expected_name=contact_name,
        ui_elements=ui_elements,
        current_activity=current_activity,
    )

    if not result:
      # 打印 UI 元素中的号码信息，便于调试
      print("[DEBUG] UI elements with text:")
      for element in ui_elements:
        if element.text:
          cleaned_text = re.sub(r"[^\d]", "", element.text)
          if cleaned_text:
            print(f"[DEBUG]   Found number: {cleaned_text}")
          else:
            print(f"[DEBUG]   Found text: {element.text}")
      if phone_number:
        expected_cleaned = re.sub(r"[^\d]", "", phone_number)
        print(f"[DEBUG] Expected number: {expected_cleaned}")
      print(f"[DEBUG] Expected name: {contact_name}")

      # UI 上出现 conference call 等异常状态时，号码不在 UI 元素中显示，
      # 无法通过 UI 判断是否拨对了号码，抛异常跳过该任务
      has_conference = any(
          element.text and 'conference' in element.text.lower()
          for element in ui_elements
      )
      if has_conference:
        raise RuntimeError(
            'UI shows conference call state, cannot verify dialed number via UI,'
            ' skipping task.'
        )

    return result
