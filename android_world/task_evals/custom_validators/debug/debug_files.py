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

"""Debug evaluators for Files app tasks.

These evaluators verify file operations (create/delete/move/rename)
by checking the file system state.

The Files app: Android system file manager
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import files as files_validator
from android_world.utils import file_utils


# 默认工作目录
_WORK_DIRECTORY = "/storage/emulated/0/Download"




class DebugFilesDeleteFile(fixed_task_eval.TaskEval):
  """固定任务：验证文件是否被删除。

  Agent 需要在 Files 文件管理器中删除指定的文件。
  验证方式：检查文件是否不存在。
  """

  complexity = 1.0

  # 固定的文件参数
  _FILE_NAME = "document_to_delete.txt"

  @property
  def goal(self) -> str:
    """任务目标。"""
    return f"In the Files app, delete the file named '{self._FILE_NAME}' in the Download folder"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空目录，创建预设文件。"""
    print("[DEBUG] Initializing files task...")
    files_validator.clear_directory(env, _WORK_DIRECTORY)
    print("[DEBUG] Working directory cleared")

    # 创建预设文件
    print(f"[DEBUG] Creating preset file: {self._FILE_NAME}")
    files_validator.create_file(
        env=env,
        file_name=self._FILE_NAME,
        directory_path=_WORK_DIRECTORY,
        content="This file should be deleted.",
    )
    print("[DEBUG] Preset file created")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    result = files_validator.validate_file_deleted(
        env=env,
        file_name=self._FILE_NAME,
        directory_path=_WORK_DIRECTORY,
    )
    return 1.0 if result else 0.0


class DebugFilesMoveFile(fixed_task_eval.TaskEval):
  """固定任务：验证文件是否被移动。

  Agent 需要在 Files 文件管理器中将文件从一个目录移动到另一个目录。
  验证方式：检查源目录文件不存在，目标目录文件存在。
  """

  complexity = 1.5

  # 固定的文件参数
  _FILE_NAME = "file_to_move.txt"
  _SOURCE_FOLDER = "Download"
  _DESTINATION_FOLDER = "Documents"

  @property
  def goal(self) -> str:
    """任务目标。"""
    return (f"In the Files app, move the file '{self._FILE_NAME}' "
            f"from {self._SOURCE_FOLDER} folder to {self._DESTINATION_FOLDER} folder")

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空目录，创建预设文件。"""
    print("[DEBUG] Initializing files task...")

    source_path = file_utils.convert_to_posix_path("/storage/emulated/0", self._SOURCE_FOLDER)
    dest_path = file_utils.convert_to_posix_path("/storage/emulated/0", self._DESTINATION_FOLDER)

    # 清空源目录
    files_validator.clear_directory(env, source_path)
    print(f"[DEBUG] Source directory cleared: {source_path}")

    # 确保目标目录存在
    files_validator.create_directory(env, self._DESTINATION_FOLDER, "/storage/emulated/0")
    files_validator.clear_directory(env, dest_path)
    print(f"[DEBUG] Destination directory ready: {dest_path}")

    # 在源目录创建预设文件
    print(f"[DEBUG] Creating preset file: {self._FILE_NAME}")
    files_validator.create_file(
        env=env,
        file_name=self._FILE_NAME,
        directory_path=source_path,
        content="This file should be moved.",
    )
    print("[DEBUG] Preset file created")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    source_path = file_utils.convert_to_posix_path("/storage/emulated/0", self._SOURCE_FOLDER)
    dest_path = file_utils.convert_to_posix_path("/storage/emulated/0", self._DESTINATION_FOLDER)

    result = files_validator.validate_file_moved(
        env=env,
        file_name=self._FILE_NAME,
        source_path=source_path,
        destination_path=dest_path,
    )
    return 1.0 if result else 0.0


class DebugFilesRenameFile(fixed_task_eval.TaskEval):
  """固定任务：验证文件是否被重命名。

  Agent 需要在 Files 文件管理器中重命名文件。
  验证方式：检查原文件名不存在，新文件名存在。
  """

  complexity = 1.0

  # 固定的文件参数
  _OLD_FILE_NAME = "old_name.txt"
  _NEW_FILE_NAME = "new_name.txt"

  @property
  def goal(self) -> str:
    """任务目标。"""
    return (f"In the Files app, rename the file '{self._OLD_FILE_NAME}' "
            f"to '{self._NEW_FILE_NAME}' in the Download folder")

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空目录，创建预设文件。"""
    print("[DEBUG] Initializing files task...")
    files_validator.clear_directory(env, _WORK_DIRECTORY)
    print("[DEBUG] Working directory cleared")

    # 创建预设文件
    print(f"[DEBUG] Creating preset file: {self._OLD_FILE_NAME}")
    files_validator.create_file(
        env=env,
        file_name=self._OLD_FILE_NAME,
        directory_path=_WORK_DIRECTORY,
        content="This file should be renamed.",
    )
    print("[DEBUG] Preset file created")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    result = files_validator.validate_file_renamed(
        env=env,
        old_name=self._OLD_FILE_NAME,
        new_name=self._NEW_FILE_NAME,
        directory_path=_WORK_DIRECTORY,
    )
    return 1.0 if result else 0.0



class DebugFilesDeleteFolder(fixed_task_eval.TaskEval):
  """固定任务：验证文件夹是否被删除。

  Agent 需要在 Files 文件管理器中删除指定的文件夹。
  验证方式：检查文件夹是否不存在。
  """

  complexity = 1.0

  # 固定的文件夹参数
  _FOLDER_NAME = "FolderToDelete"

  @property
  def goal(self) -> str:
    """任务目标。"""
    return f"In the Files app, delete the folder named '{self._FOLDER_NAME}' in the Download folder"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空目录，创建预设文件夹。"""
    print("[DEBUG] Initializing files task...")
    files_validator.clear_directory(env, _WORK_DIRECTORY)
    print("[DEBUG] Working directory cleared")

    # 创建预设文件夹
    print(f"[DEBUG] Creating preset folder: {self._FOLDER_NAME}")
    files_validator.create_directory(
        env=env,
        directory_name=self._FOLDER_NAME,
        parent_path=_WORK_DIRECTORY,
    )
    print("[DEBUG] Preset folder created")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    folder_path = file_utils.convert_to_posix_path(_WORK_DIRECTORY, self._FOLDER_NAME)
    result = files_validator.validate_directory_deleted(
        env=env,
        directory_path=folder_path,
    )
    return 1.0 if result else 0.0


class DebugFilesDeleteMultipleFiles(fixed_task_eval.TaskEval):
  """固定任务：验证多个文件是否被删除。

  Agent 需要在 Files 文件管理器中删除多个文件。
  验证方式：检查所有文件是否不存在。
  """

  complexity = 1.5

  # 固定的文件参数
  _FILE_NAMES = ["file_a.txt", "file_b.txt", "file_c.txt"]

  @property
  def goal(self) -> str:
    """任务目标。"""
    files_str = ", ".join(self._FILE_NAMES)
    return f"In the Files app, delete the following files from the Download folder: {files_str}"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空目录，创建预设文件。"""
    print("[DEBUG] Initializing files task...")
    files_validator.clear_directory(env, _WORK_DIRECTORY)
    print("[DEBUG] Working directory cleared")

    # 创建预设文件
    print("[DEBUG] Creating preset files...")
    for file_name in self._FILE_NAMES:
      files_validator.create_file(
          env=env,
          file_name=file_name,
          directory_path=_WORK_DIRECTORY,
          content=f"Content of {file_name}",
      )
    print("[DEBUG] Preset files created")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    result = files_validator.validate_files_deleted(
        env=env,
        file_names=self._FILE_NAMES,
        directory_path=_WORK_DIRECTORY,
    )
    return 1.0 if result else 0.0