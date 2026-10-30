

"""Task for contacts apps."""

import random
import re
from typing import Optional
from absl import logging
from android_world.env import interface
from android_world.env import representation_utils
from android_world.task_evals import task_eval
from android_world.task_evals.common_validators import contacts_validators
from android_world.utils import contacts_utils
from android_world.utils import fuzzy_match_lib


# ============================================================================
# 封装验证函数：检查联系人操作是否成功
# ============================================================================

def get_contacts(env: interface.AsyncEnv) -> list[contacts_utils.Contact]:
    """获取所有联系人列表。

    Args:
        env: Android 环境接口。

    Returns:
        Contact 对象列表。
    """
    contacts = contacts_utils.list_contacts(env.controller)
    print(f"[DEBUG] Found {len(contacts)} contacts")
    return contacts


def clear_contacts(env: interface.AsyncEnv) -> None:
    """清空所有联系人。

    Args:
        env: Android 环境接口。
    """
    contacts_utils.clear_contacts(env.controller)
    print("[DEBUG] All contacts cleared")


def add_contact(
    env: interface.AsyncEnv,
    name: str,
    phone_number: str,
) -> None:
    """添加一个联系人。

    Args:
        env: Android 环境接口。
        name: 联系人姓名。
        phone_number: 电话号码。
    """
    contacts_utils.add_contact(name, phone_number, env.controller)
    print(f"[DEBUG] Added contact: {name}")


def _normalize_phone(phone: str) -> str:
    """标准化电话号码（移除非数字字符）。"""
    return contacts_utils.clean_phone_number(phone)


def _normalize_name(name: str) -> str:
    """标准化姓名用于模糊匹配。"""
    return name.lower().strip()


def _contact_matches(
    contact: contacts_utils.Contact,
    expected_name: str,
    expected_number: str,
    expected_company: Optional[str] = None,
    expected_email: Optional[str] = None,
    fuzzy_match_name: bool = True,
) -> bool:
    """检查联系人是否匹配给定条件。

    Args:
        contact: 要检查的联系人。
        expected_name: 期望的姓名。
        expected_number: 期望的电话号码。
        expected_company: 期望的公司（可选）。
        expected_email: 期望的邮箱（可选）。
        fuzzy_match_name: 是否对姓名使用模糊匹配。

    Returns:
        True 如果联系人匹配所有提供的条件。
    """
    # 检查姓名
    if fuzzy_match_name:
        if _normalize_name(contact.name) != _normalize_name(expected_name):
            return False
    else:
        if contact.name != expected_name:
            return False

    # 检查电话号码
    if _normalize_phone(contact.number) != _normalize_phone(expected_number):
        return False

    # 检查公司（如果指定了）
    if expected_company is not None:
        if _normalize_name(contact.company) != _normalize_name(expected_company):
            return False

    # 检查邮箱（如果指定了）
    if expected_email is not None:
        if contact.email.lower().strip() != expected_email.lower().strip():
            return False

    return True


def validate_contact_added(
    env: interface.AsyncEnv,
    before_contacts: list[contacts_utils.Contact],
    expected_name: str,
    expected_number: str,
    expected_company: Optional[str] = None,
    expected_email: Optional[str] = None,
    check_integrity: bool = True,
    fuzzy_match_name: bool = True,
) -> bool:
    """验证联系人是否被正确添加。

    Args:
        env: Android 环境接口。
        before_contacts: 任务执行前的联系人列表。
        expected_name: 期望的联系人姓名。
        expected_number: 期望的电话号码。
        expected_company: 期望的公司（可选）。
        expected_email: 期望的邮箱（可选）。
        check_integrity: 是否检查其他联系人完整性。
        fuzzy_match_name: 是否对姓名使用模糊匹配。

    Returns:
        True 如果验证通过，False 否则。
    """
    after_contacts = get_contacts(env)

    print(f"[DEBUG] Before contacts: {len(before_contacts)}")
    print(f"[DEBUG] After contacts: {len(after_contacts)}")
    print(f"[DEBUG] Expected name: '{expected_name}'")
    print(f"[DEBUG] Expected number: '{expected_number}'")
    if expected_company:
        print(f"[DEBUG] Expected company: '{expected_company}'")
    if expected_email:
        print(f"[DEBUG] Expected email: '{expected_email}'")

    # 打印所有联系人
    for i, contact in enumerate(after_contacts):
        print(f"[DEBUG] Contact {i}: name='{contact.name}', number='{contact.number}', company='{contact.company}', email='{contact.email}'")

    # 查找匹配的联系人
    for contact in after_contacts:
        if not _contact_matches(contact, expected_name, expected_number, expected_company, expected_email, fuzzy_match_name):
            continue

        # 检查是否是新添加的
        if contact not in before_contacts:
            if check_integrity:
                # 验证其他联系人未被删除
                for old_contact in before_contacts:
                    if old_contact not in after_contacts:
                        return False
                if len(after_contacts) != len(before_contacts) + 1:
                    return False
            print(f"[DEBUG] Contact addition validated: True")
            return True

    print(f"[DEBUG] Contact addition validated: False")
    return False


def validate_contacts_added(
    env: interface.AsyncEnv,
    before_contacts: list[contacts_utils.Contact],
    expected_contacts: list[dict],
    check_integrity: bool = True,
    fuzzy_match_name: bool = True,
) -> bool:
    """验证多个联系人是否被正确添加。

    Args:
        env: Android 环境接口。
        before_contacts: 任务执行前的联系人列表。
        expected_contacts: 期望添加的联系人列表，每个元素是包含 name, number, company, email 等字段的字典。
        check_integrity: 是否检查其他联系人完整性。
        fuzzy_match_name: 是否对姓名使用模糊匹配。

    Returns:
        True 如果验证通过，False 否则。
    """
    after_contacts = get_contacts(env)

    print(f"[DEBUG] Before contacts: {len(before_contacts)}")
    print(f"[DEBUG] After contacts: {len(after_contacts)}")

    # 打印所有联系人
    for i, contact in enumerate(after_contacts):
        print(f"[DEBUG] Contact {i}: name='{contact.name}', number='{contact.number}', company='{contact.company}', email='{contact.email}'")

    # 验证每个联系人
    for contact_data in expected_contacts:
        name = contact_data["name"]
        number = contact_data["number"]
        company = contact_data.get("company")
        email = contact_data.get("email")
        print(f"[DEBUG] Expected contact: name='{name}', number='{number}', company='{company}', email='{email}'")

        # 查找匹配的联系人
        found = False
        for contact in after_contacts:
            if not _contact_matches(contact, name, number, company, email, fuzzy_match_name):
                continue

            # 检查是否是新添加的
            if contact not in before_contacts:
                found = True
                break

        if not found:
            print(f"[DEBUG] Failed to validate contact: {name}")
            return False

    # 检查数量是否正确
    if check_integrity:
        expected_count = len(expected_contacts)
        actual_count = len(after_contacts) - len(before_contacts)
        if actual_count != expected_count:
            print(f"[DEBUG] Count mismatch: expected {expected_count} new contacts, got {actual_count}")
            return False

    print(f"[DEBUG] Multiple contacts addition validated: True")
    return True


def validate_contact_deleted(
    env: interface.AsyncEnv,
    before_contacts: list[contacts_utils.Contact],
    contact_name: str,
    check_integrity: bool = True,
    fuzzy_match_name: bool = True,
) -> bool:
    """验证联系人是否被正确删除。

    Args:
        env: Android 环境接口。
        before_contacts: 任务执行前的联系人列表。
        contact_name: 要删除的联系人姓名。
        check_integrity: 是否检查其他联系人完整性。
        fuzzy_match_name: 是否对姓名使用模糊匹配。

    Returns:
        True 如果验证通过，False 否则。
    """
    after_contacts = get_contacts(env)

    print(f"[DEBUG] Before contacts: {len(before_contacts)}")
    print(f"[DEBUG] After contacts: {len(after_contacts)}")
    print(f"[DEBUG] Looking for contact to delete: name='{contact_name}'")

    # 查找要删除的联系人
    contact_to_delete = None
    for contact in before_contacts:
        if fuzzy_match_name:
            if _normalize_name(contact.name) == _normalize_name(contact_name):
                contact_to_delete = contact
                break
        else:
            if contact.name == contact_name:
                contact_to_delete = contact
                break

    if contact_to_delete is None:
        print(f"[DEBUG] No contact found with name: {contact_name}")
        return False

    print(f"[DEBUG] Contact to delete: name='{contact_to_delete.name}', number='{contact_to_delete.number}'")

    # 检查联系人是否已不在列表中
    if contact_to_delete in after_contacts:
        print(f"[DEBUG] Contact still exists in after_contacts")
        return False

    if check_integrity:
        # 验证其他联系人未被删除
        for old_contact in before_contacts:
            if old_contact != contact_to_delete and old_contact not in after_contacts:
                return False
        if len(after_contacts) != len(before_contacts) - 1:
            return False

    print(f"[DEBUG] Contact deletion validated: True")
    return True


def validate_contact_number_changed(
    env: interface.AsyncEnv,
    before_contacts: list[contacts_utils.Contact],
    contact_name: str,
    new_number: str,
    fuzzy_match_name: bool = True,
) -> bool:
    """验证联系人电话号码是否被修改。

    Args:
        env: Android 环境接口。
        before_contacts: 任务执行前的联系人列表。
        contact_name: 联系人姓名。
        new_number: 新的电话号码。
        fuzzy_match_name: 是否对姓名使用模糊匹配。

    Returns:
        True 如果验证通过，False 否则。
    """
    after_contacts = get_contacts(env)

    print(f"[DEBUG] Before contacts: {len(before_contacts)}")
    print(f"[DEBUG] After contacts: {len(after_contacts)}")
    print(f"[DEBUG] Looking for contact: name='{contact_name}'")
    print(f"[DEBUG] Expected new number: '{new_number}'")

    # 查找联系人
    for contact in after_contacts:
        if fuzzy_match_name:
            if _normalize_name(contact.name) == _normalize_name(contact_name):
                if _normalize_phone(contact.number) == _normalize_phone(new_number):
                    print(f"[DEBUG] Contact number changed successfully")
                    return True
                else:
                    print(f"[DEBUG] Contact found but number is '{contact.number}', expected '{new_number}'")
                    return False
        else:
            if contact.name == contact_name:
                if _normalize_phone(contact.number) == _normalize_phone(new_number):
                    print(f"[DEBUG] Contact number changed successfully")
                    return True
                else:
                    print(f"[DEBUG] Contact found but number is '{contact.number}', expected '{new_number}'")
                    return False

    print(f"[DEBUG] Contact not found")
    return False


def find_contact_by_name(
    contacts: list[contacts_utils.Contact],
    name: str,
    fuzzy_match: bool = True,
) -> Optional[contacts_utils.Contact]:
    """按姓名查找联系人。

    Args:
        contacts: 联系人列表。
        name: 要搜索的姓名。
        fuzzy_match: 是否使用模糊匹配。

    Returns:
        第一个匹配的联系人，如果未找到则返回 None。
    """
    if fuzzy_match:
        normalized_name = _normalize_name(name)
        for contact in contacts:
            if _normalize_name(contact.name) == normalized_name:
                return contact
    else:
        for contact in contacts:
            if contact.name == name:
                return contact
    return None


class ContactsAddContact(contacts_validators.AddContact):
  """Task for adding a new contact."""

  complexity = 1.2
  app_names = ("contacts",)
  template = "Create a new contact for {name}. Their number is {number}."


def _contact_info_is_entered(
    first: str,
    last: str,
    phone: str,
    phone_label: str,
    ui_elements: list[representation_utils.UIElement],
) -> bool:
  """Checks if UI elements contain requested contact info.

  Specifically, it checks if current screen is the new contact screen and if the
  screen shows the function arguments filled out for the contacts.

  Args:
    first: First name.
    last: Last name.
    phone: Phone number.
    phone_label: Label for phone number.
    ui_elements: UI elements on screen.

  Returns:
    True if contact form is filled out.
  """
  first_name_element = None
  last_name_element = None
  phone_element = None
  phone_label_element = None

  # Mobile can appear twice on the screen, making this is a difficult edge case.
  # Do not use this input.
  assert phone_label != "Mobile"

  for element in ui_elements:
    if (
        element.text
        and fuzzy_match_lib.fuzzy_match(element.text, first)
        and element.hint_text == "First name"
    ):
      first_name_element = element
    elif (
        element.text
        and fuzzy_match_lib.fuzzy_match(element.text, last)
        and element.hint_text == "Last name"
    ):
      last_name_element = element
    elif element.text and (
        re.sub(r"\D", "", element.text) == re.sub(r"\D", "", phone)
        and element.hint_text == "Phone"
    ):
      phone_element = element
    elif (
        element.text == phone_label
        and element.content_description == phone_label + " Phone"
    ):
      phone_label_element = element

  # Content description may not be set properly, so we try to find the phone
  # label element by its text and its position if it is not found above
  if phone_element and phone_label_element is None:
    phone_label_element = _find_phone_label_element(
        phone_element, phone_label, ui_elements
    )
  if (
      first_name_element is None
      or last_name_element is None
      or phone_element is None
      or phone_label_element is None
  ):
    if first_name_element is None:
      logging.info("Missing 'first' UI element")
    if last_name_element is None:
      logging.info("Missing 'last' UI element")
    if phone_element is None:
      logging.info("Missing 'phone' UI element")
    if phone_label_element is None:
      logging.info("Missing 'phone_label' UI element")
    return False

  return True


def _find_phone_label_element(
    phone_element: representation_utils.UIElement,
    phone_label: str,
    ui_elements: list[representation_utils.UIElement],
) -> None | representation_utils.UIElement:
  for element in ui_elements:
    if element.text == phone_label and _vertically_adjacent(
        phone_element, element
    ):
      return element
  return None


def _vertically_adjacent(
    element1: representation_utils.UIElement,
    element2: representation_utils.UIElement,
) -> bool:
  if not element1.bbox_pixels or not element2.bbox_pixels:
    return False
  return (
      element1.bbox_pixels.y_max
      <= element2.bbox_pixels.y_min
      <= element1.bbox_pixels.y_max + element1.bbox_pixels.height
  )


# class ContactsNewContactDraft(task_eval.TaskEval):
#   """Task for entering contact info, but *not* hitting save."""

#   app_names = ("contacts",)
#   complexity = 1.2
#   schema = {
#       "type": "object",
#       "properties": {
#           "first": {"type": "string"},
#           "last": {"type": "string"},
#           "phone": {"type": "string"},
#           "phone_label": {"type": "string"},
#       },
#       "required": ["first", "last", "phone", "phone_label"],
#   }
#   template = (
#       "Go to the new contact screen and enter the following details: First"
#       " Name: {first}, Last Name: {last}, Phone: {phone}, Phone Label:"
#       " {phone_label}. Do NOT hit save."
#   )

#   @classmethod
#   def generate_random_params(cls) -> dict[str, str]:
#     first_names = [
#         "Alice",
#         "Bob",
#         "Charlie",
#         "David",
#         "Eva",
#         "Frank",
#         "Grace",
#         "Hannah",
#         "Ivan",
#         "Jack",
#     ]
#     last_names = [
#         "Johnson",
#         "Smith",
#         "Brown",
#         "Taylor",
#         "Adams",
#         "Wilson",
#         "Lee",
#         "White",
#         "Harris",
#         "Clark",
#     ]
#     phone_labels = ["Home", "Work"]

#     first = random.choice(first_names)
#     last = random.choice(last_names)
#     phone = (
#         f"{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
#     )
#     phone_label = random.choice(phone_labels)

#     params = {
#         "first": first,
#         "last": last,
#         "phone": phone,
#         "phone_label": phone_label,
#     }

#     return params

#   def is_successful(
#       self,
#       env: interface.AsyncEnv,
#   ) -> float:
#     super().is_successful(env)
#     ui_elements = representation_utils.forest_to_ui_elements(
#         env.get_state().forest,
#         exclude_invisible_elements=False,
#     )
#     return (
#         1.0
#         if _contact_info_is_entered(
#             ui_elements=ui_elements,
#             first=self.params["first"],
#             last=self.params["last"],
#             phone=self.params["phone"],
#             phone_label=self.params["phone_label"],
#         )
#         else 0.0
#     )
