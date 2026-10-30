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

"""Debug evaluators for Joplin note tasks.

These evaluators verify note operations (add/delete) by comparing
the before and after state of the Joplin database.
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import joplin
from android_world.task_evals.information_retrieval import joplin_app_utils


class DebugJoplinAddNote(fixed_task_eval.TaskEval):
  """固定任务：验证笔记是否被添加到指定 notebook。

  Agent 需要在 Joplin 中添加一个指定的笔记到指定 notebook。
  验证方式：比较任务执行前后的数据库状态。
  """

  complexity = 1.0

  # 固定的笔记参数
  _NOTE_TITLE = "Meeting Notes"
  _NOTE_BODY = "Discussion points:\n1. Project timeline\n2. Budget review\n3. Next steps"
  _NOTE_NOTEBOOK = "Work"

  @property
  def goal(self) -> str:
    """任务目标。"""
    return f"In Joplin, create a new note titled '{self._NOTE_TITLE}' in the '{self._NOTE_NOTEBOOK}' notebook with the body '{self._NOTE_BODY}'"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空数据库，存储初始状态。"""
    print("[DEBUG] Clearing Joplin database...")
    joplin_app_utils.clear_dbs(env)
    print("[DEBUG] Joplin database cleared")
    self._before_notes = joplin.get_notes(env)
    print(f"[DEBUG] Stored before state: {len(self._before_notes)} notes")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_notes'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = joplin.validate_note_added(
        env=env,
        before_notes=self._before_notes,
        expected_title=self._NOTE_TITLE,
        expected_body=self._NOTE_BODY,
        expected_notebook=self._NOTE_NOTEBOOK,
    )
    return 1.0 if result else 0.0


class DebugJoplinDeleteNote(fixed_task_eval.TaskEval):
  """固定任务：验证笔记是否被删除。

  Agent 需要在 Joplin 中删除指定 notebook 中的笔记。
  验证方式：比较任务执行前后的数据库状态。
  """

  complexity = 1.0

  # 固定的笔记标题和 notebook
  _NOTE_TITLE = "Meeting Notes"
  _NOTE_NOTEBOOK = "Work"

  @property
  def goal(self) -> str:
    """任务目标。"""
    return f"In Joplin, delete the note titled '{self._NOTE_TITLE}' in the '{self._NOTE_NOTEBOOK}' notebook"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空数据库，添加预设笔记，存储初始状态。"""
    print("[DEBUG] Clearing Joplin database...")
    joplin_app_utils.clear_dbs(env)
    print("[DEBUG] Joplin database cleared")

    # 添加预设笔记到指定 notebook
    print(f"[DEBUG] Adding preset note: {self._NOTE_TITLE} to notebook: {self._NOTE_NOTEBOOK}")
    folder_mapping = {}
    preset_note = joplin_app_utils.create_note(
        folder=self._NOTE_NOTEBOOK,
        title=self._NOTE_TITLE,
        body="Discussion points:\n1. Project timeline\n2. Budget review\n3. Next steps",
        folder_mapping=folder_mapping,
        env=env,
    )
    joplin_app_utils.add_notes([preset_note], env)
    print("[DEBUG] Preset note added")

    self._before_notes = joplin.get_notes(env)
    print(f"[DEBUG] Stored before state: {len(self._before_notes)} notes")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_notes'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = joplin.validate_joplin_note_deleted(
        env=env,
        before_notes=self._before_notes,
        note_title=self._NOTE_TITLE,
        notebook=self._NOTE_NOTEBOOK,
    )
    return 1.0 if result else 0.0


class DebugJoplinAddMultipleNotes(fixed_task_eval.TaskEval):
  """固定任务：验证多个笔记是否被添加到指定 notebook。

  Agent 需要在 Joplin 中添加多个笔记到指定 notebook。
  验证方式：比较任务执行前后的数据库状态。
  """

  complexity = 1.5

  # 固定的笔记参数
  _NOTES = [
      {
          "title": "Shopping List",
          "body": "- Milk\n- Eggs\n- Bread\n- Cheese",
          "notebook": "Personal",
      },
      {
          "title": "Project Ideas",
          "body": "1. Mobile app for habit tracking\n2. Web scraper for price comparison",
          "notebook": "Work",
      },
  ]

  @property
  def goal(self) -> str:
    """任务目标。"""
    return ("In Joplin, create two notes: 'Shopping List' with grocery items in the 'Personal' notebook, "
            "and 'Project Ideas' with two project ideas in the 'Work' notebook")

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空数据库，存储初始状态。"""
    print("[DEBUG] Clearing Joplin database...")
    joplin_app_utils.clear_dbs(env)
    print("[DEBUG] Joplin database cleared")
    self._before_notes = joplin.get_notes(env)
    print(f"[DEBUG] Stored before state: {len(self._before_notes)} notes")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_notes'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = joplin.validate_notes_added(
        env=env,
        before_notes=self._before_notes,
        expected_notes=self._NOTES,
    )
    return 1.0 if result else 0.0


class DebugJoplinDeleteMultipleNotes(fixed_task_eval.TaskEval):
  """固定任务：验证多个笔记是否被删除。

  Agent 需要在 Joplin 中删除指定 notebook 中的多个笔记。
  验证方式：比较任务执行前后的数据库状态。
  """

  complexity = 1.5

  # 固定的笔记标题和 notebook
  _NOTE_TITLES = ["Shopping List", "Project Ideas"]
  _NOTE_NOTEBOOK = "Personal"

  @property
  def goal(self) -> str:
    """任务目标。"""
    return f"In Joplin, delete both 'Shopping List' and 'Project Ideas' notes from the '{self._NOTE_NOTEBOOK}' notebook"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空数据库，添加预设笔记，存储初始状态。"""
    print("[DEBUG] Clearing Joplin database...")
    joplin_app_utils.clear_dbs(env)
    print("[DEBUG] Joplin database cleared")

    # 添加预设笔记到指定 notebook
    print(f"[DEBUG] Adding preset notes to notebook: {self._NOTE_NOTEBOOK}")
    folder_mapping = {}
    preset_notes = [
        joplin_app_utils.create_note(
            folder=self._NOTE_NOTEBOOK,
            title="Shopping List",
            body="- Milk\n- Eggs\n- Bread\n- Cheese",
            folder_mapping=folder_mapping,
            env=env,
        ),
        joplin_app_utils.create_note(
            folder=self._NOTE_NOTEBOOK,
            title="Project Ideas",
            body="1. Mobile app for habit tracking\n2. Web scraper for price comparison",
            folder_mapping=folder_mapping,
            env=env,
        ),
    ]
    joplin_app_utils.add_notes(preset_notes, env)
    print("[DEBUG] Preset notes added")

    self._before_notes = joplin.get_notes(env)
    print(f"[DEBUG] Stored before state: {len(self._before_notes)} notes")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_notes'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = joplin.validate_joplin_notes_deleted(
        env=env,
        before_notes=self._before_notes,
        note_titles=self._NOTE_TITLES,
        notebook=self._NOTE_NOTEBOOK,
    )
    return 1.0 if result else 0.0