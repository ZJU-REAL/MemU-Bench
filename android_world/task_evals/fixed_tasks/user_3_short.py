

"""固定任务：短任务集合。

包含以下任务：
- GalleryDeletePhoto: 删除相册中的指定图片
- GalleryDeleteScreenshot: 删除相册中的截图
- SMSSendVerificationCodeFromScreenshot: 发送截图中的验证码给来电者
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import files as files_validator
from android_world.task_evals.custom_validators import sms as sms_validator


class User3Short_GalleryDeletePhoto(fixed_task_eval.TaskEval):
  """固定任务：删除相册中的指定图片。

  Agent 需要在 Simple Gallery Pro 中删除指定的收据图片。
  验证方式：检查文件系统中该图片是否已被删除，且其他文件未被误删。
  """

  app_name = "simple gallery"

  complexity = 4.0

  # 固定的图片参数
  _FILE_NAME = "receipt_001.jpg"
  _FILE_DIRECTORY = "/sdcard/DCIM"
  _SNAPSHOT_NAME = "snapshot_3_short"

  def __init__(self):
    super().__init__()
    self._initial_files = None

  @property
  def goal(self) -> str:
    return f"Delete the receipt I was looking at earlier from the {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Delete the receipt named {self._FILE_NAME} from the {self.app_name} app."
  
  @property
  def information(self) -> str:
    return "I saw a receipt with 'Quality First' printed on it."
  
  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._initial_files = [
        f.name for f in files_validator.get_files_in_directory(
            env, self._FILE_DIRECTORY
        )
    ]
    print(f"[DEBUG] Initializing gallery delete photo task...")
    print(f"[DEBUG] Target file: {self._FILE_NAME} in {self._FILE_DIRECTORY}")
    print(f"[DEBUG] Initial files in directory: {self._initial_files}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = files_validator.validate_file_deleted(
        env=env,
        file_name=self._FILE_NAME,
        directory_path=self._FILE_DIRECTORY,
        initial_files=self._initial_files,
    )
    return 1.0 if result else 0.0


class User3Short_GalleryDeleteScreenshot(fixed_task_eval.TaskEval):
  """固定任务：删除相册中的截图。

  Agent 需要在 Simple Gallery Pro 中删除看小说时不小心截的图。
  验证方式：检查文件系统中该截图是否已被删除，且其他文件未被误删。
  """

  app_name = "simple gallery"

  complexity = 4.0

  # 固定的截图参数
  _FILE_NAME = "screenshot.png"
  _FILE_DIRECTORY = "/sdcard/DCIM"
  _SNAPSHOT_NAME = "snapshot_3_short"

  def __init__(self):
    super().__init__()
    self._initial_files = None

  @property
  def goal(self) -> str:
    return f"Delete the screenshot I accidentally took while reading a novel earlier from the {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Delete the screenshot named {self._FILE_NAME} from the {self.app_name} app."

  @property
  def information(self) -> str:
    return "I accidentally took a screenshot while reading the book '三体'."
  
  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._initial_files = [
        f.name for f in files_validator.get_files_in_directory(
            env, self._FILE_DIRECTORY
        )
    ]
    print(f"[DEBUG] Initializing gallery delete screenshot task...")
    print(f"[DEBUG] Target file: {self._FILE_NAME} in {self._FILE_DIRECTORY}")
    print(f"[DEBUG] Initial files in directory: {self._initial_files}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = files_validator.validate_file_deleted(
        env=env,
        file_name=self._FILE_NAME,
        directory_path=self._FILE_DIRECTORY,
        initial_files=self._initial_files,
    )
    return 1.0 if result else 0.0


class User3Short_SMSSendVerificationCodeFromScreenshot(fixed_task_eval.TaskEval):
  """固定任务：将截图中的验证码发送给来电者。

  Agent 需要查看相册中截图的验证码，并通过短信发送给刚才打电话来的人。
  验证方式：检查短信数据库中是否有发送给目标号码的短信，且内容匹配。
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  # 固定的短信参数
  _PHONE_NUMBER = "127843390"
  _MESSAGE_BODY = "4444"
  _SNAPSHOT_NAME = "snapshot_3_short"

  @property
  def goal(self) -> str:
    return ("Send the verification code"
            f"to the person who just called me via {self.app_name} app.")

  @property
  def full_goal(self) -> str:
    return (f"Send the verification code: {self._MESSAGE_BODY} "
            f"to the number {self._PHONE_NUMBER} via {self.app_name} app.")
  
  @property
  def information(self) -> str:
    return "I received a verification code from Tomato Novel and took a screenshot, then saved it to the Simple Gallery app."
  
  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing SMS send verification code from screenshot task...")
    print(f"[DEBUG] Target: {self._PHONE_NUMBER}")
    print(f"[DEBUG] Message: {self._MESSAGE_BODY}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = sms_validator.validate_sms_sent(
        env=env,
        goal=self.full_goal,
        phone_number=self._PHONE_NUMBER,
        expected_body=self._MESSAGE_BODY,
    )
    return 1.0 if result else 0.0