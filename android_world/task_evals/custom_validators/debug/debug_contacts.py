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

"""Debug evaluators for Contacts app tasks.

These evaluators verify contact operations (add/delete) by checking
the contacts content provider.
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import contacts as contacts_validator


class DebugContactAdd(fixed_task_eval.TaskEval):
  """固定任务：验证联系人是否被添加。

  Agent 需要在联系人应用中添加一个联系人。
  验证方式：比较任务执行前后的联系人列表状态。
  """

  complexity = 1.0

  # 固定的联系人参数
  _CONTACT_NAME = "John Smith"
  _CONTACT_NUMBER = "555-123-4567"
  _CONTACT_COMPANY = "Google"
  _CONTACT_EMAIL = "john@example.com"

  @property
  def goal(self) -> str:
    """任务目标。"""
    return (f"In the Contacts app, add a new contact named '{self._CONTACT_NAME}' "
            f"with phone number '{self._CONTACT_NUMBER}', "
            f"company '{self._CONTACT_COMPANY}', and email '{self._CONTACT_EMAIL}'")

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空联系人，存储初始状态。"""
    print("[DEBUG] Initializing contacts task...")
    contacts_validator.clear_contacts(env)
    print("[DEBUG] Contacts cleared")
    self._before_contacts = contacts_validator.get_contacts(env)
    print(f"[DEBUG] Stored before state: {len(self._before_contacts)} contacts")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_contacts'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = contacts_validator.validate_contact_added(
        env=env,
        before_contacts=self._before_contacts,
        expected_name=self._CONTACT_NAME,
        expected_number=self._CONTACT_NUMBER,
        expected_company=self._CONTACT_COMPANY,
        expected_email=self._CONTACT_EMAIL,
    )
    return 1.0 if result else 0.0


class DebugContactDelete(fixed_task_eval.TaskEval):
  """固定任务：验证联系人是否被删除。

  Agent 需要在联系人应用中删除指定的联系人。
  验证方式：比较任务执行前后的联系人列表状态。
  """

  complexity = 1.0

  # 固定的联系人名称
  _CONTACT_NAME = "John Smith"

  @property
  def goal(self) -> str:
    """任务目标。"""
    return f"In the Contacts app, delete the contact named '{self._CONTACT_NAME}'"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空联系人，添加预设联系人，存储初始状态。"""
    print("[DEBUG] Initializing contacts task...")
    contacts_validator.clear_contacts(env)
    print("[DEBUG] Contacts cleared")

    # 添加预设联系人
    print(f"[DEBUG] Adding preset contact: {self._CONTACT_NAME}")
    contacts_validator.add_contact(
        env=env,
        name=self._CONTACT_NAME,
        phone_number="555-123-4567",
    )
    print("[DEBUG] Preset contact added")

    self._before_contacts = contacts_validator.get_contacts(env)
    print(f"[DEBUG] Stored before state: {len(self._before_contacts)} contacts")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_contacts'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = contacts_validator.validate_contact_deleted(
        env=env,
        before_contacts=self._before_contacts,
        contact_name=self._CONTACT_NAME,
    )
    return 1.0 if result else 0.0


class DebugContactAddMultiple(fixed_task_eval.TaskEval):
  """固定任务：验证多个联系人是否被添加。

  Agent 需要在联系人应用中添加多个联系人。
  验证方式：比较任务执行前后的联系人列表状态。
  """

  complexity = 1.5

  # 固定的联系人参数（包含公司和邮箱）
  _CONTACTS = [
      {"name": "Alice Brown", "number": "555-111-2222", "company": "Apple", "email": "alice@apple.com"},
      {"name": "Bob Wilson", "number": "555-333-4444", "company": "Microsoft", "email": "bob@microsoft.com"},
  ]

  @property
  def goal(self) -> str:
    """任务目标。"""
    contacts_str = ", ".join(
        f"'{c['name']}' ({c['number']}, {c['company']}, {c['email']})" for c in self._CONTACTS
    )
    return f"In the Contacts app, add the following contacts: {contacts_str}"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空联系人，存储初始状态。"""
    print("[DEBUG] Initializing contacts task...")
    contacts_validator.clear_contacts(env)
    print("[DEBUG] Contacts cleared")
    self._before_contacts = contacts_validator.get_contacts(env)
    print(f"[DEBUG] Stored before state: {len(self._before_contacts)} contacts")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_contacts'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = contacts_validator.validate_contacts_added(
        env=env,
        before_contacts=self._before_contacts,
        expected_contacts=self._CONTACTS,
    )
    return 1.0 if result else 0.0


class DebugContactDeleteMultiple(fixed_task_eval.TaskEval):
  """固定任务：验证多个联系人是否被删除。

  Agent 需要在联系人应用中删除多个联系人。
  验证方式：比较任务执行前后的联系人列表状态。
  """

  complexity = 1.5

  # 固定的联系人名称列表
  _CONTACT_NAMES = ["Alice Brown", "Bob Wilson"]

  @property
  def goal(self) -> str:
    """任务目标。"""
    names_str = " and ".join(self._CONTACT_NAMES)
    return f"In the Contacts app, delete the contacts named {names_str}"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空联系人，添加预设联系人，存储初始状态。"""
    print("[DEBUG] Initializing contacts task...")
    contacts_validator.clear_contacts(env)
    print("[DEBUG] Contacts cleared")

    # 添加预设联系人
    print("[DEBUG] Adding preset contacts...")
    preset_contacts = [
        ("Alice Brown", "555-111-2222"),
        ("Bob Wilson", "555-333-4444"),
    ]
    for name, number in preset_contacts:
      contacts_validator.add_contact(env=env, name=name, phone_number=number)
    print("[DEBUG] Preset contacts added")

    self._before_contacts = contacts_validator.get_contacts(env)
    print(f"[DEBUG] Stored before state: {len(self._before_contacts)} contacts")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_contacts'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    # 验证每个联系人是否被删除
    for name in self._CONTACT_NAMES:
      result = contacts_validator.validate_contact_deleted(
          env=env,
          before_contacts=self._before_contacts,
          contact_name=name,
          check_integrity=False,
      )
      if not result:
        print(f"[DEBUG] Failed to delete contact: {name}")
        return 0.0

    print("[DEBUG] All contacts deleted successfully")
    return 1.0