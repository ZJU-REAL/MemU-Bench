"""固定任务：短任务集合。

包含以下任务：
- User11Short_FilesDeletePaper: 删除 Attention Is All You Need 论文
- User11Short_SMSSendNewPhonePrice: 给 Sarah Jones 发送新手机价格短信
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import files as files_validator
from android_world.task_evals.custom_validators import recipe as recipe_validator
from android_world.task_evals.custom_validators import sms as sms_validator



class User11Short_FilesDeletePaper(fixed_task_eval.TaskEval):
  """固定任务：删除 Attention Is All You Need 论文（两份）。

  Agent 需要在文件管理器中删除两份 Attention Is All You Need 论文。
  验证方式：检查文件系统中两份论文是否均已被删除，且其他文件未被误删。
  """

  app_name = "files"

  complexity = 4.0

  _FILE_NAMES = [
      "Vaswani 等 - 2023 - Attention Is All You Need.pdf",
      "Vaswani 等 - 2023 - Attention Is All You Need copy.pdf",
  ]
  _FILE_DIRECTORY = "/sdcard/Download"
  _SNAPSHOT_NAME = "snapshot_11_short"

  def __init__(self):
    super().__init__()
    self._initial_files = None

  @property
  def goal(self) -> str:
    return f"Delete the paper I read today, it's too deep for me, in the {self.app_name} app."

  @property
  def full_goal(self) -> str:
    names = " and ".join(self._FILE_NAMES)
    return f"Delete the papers named {names} from the {self.app_name} app."

  @property
  def information(self):
    return "The paper I just read seems to have 'Attention' in its title."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._initial_files = [
        f.name for f in files_validator.get_files_in_directory(
            env, self._FILE_DIRECTORY
        )
    ]
    print(f"[DEBUG] Initializing files delete paper task...")
    print(f"[DEBUG] Target files: {self._FILE_NAMES} in {self._FILE_DIRECTORY}")
    print(f"[DEBUG] Initial files in directory: {self._initial_files}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    current_files = [
        f.name for f in files_validator.get_files_in_directory(
            env, self._FILE_DIRECTORY
        )
    ]
    print(f"[DEBUG] Current files in directory: {current_files}")

    # 检查目标文件是否都被删除
    for file_name in self._FILE_NAMES:
      exists = files_validator.file_exists(env, file_name, self._FILE_DIRECTORY)
      print(f"[DEBUG] File '{file_name}' exists: {exists}")
      if exists:
        print(f"[DEBUG] Target file '{file_name}' was not deleted")
        return 0.0

    # 检查其他文件是否被误删（排除目标文件）
    for file_name in self._initial_files:
      if file_name not in self._FILE_NAMES:
        exists = files_validator.file_exists(env, file_name, self._FILE_DIRECTORY)
        if not exists:
          print(f"[DEBUG] Unexpected file deletion: {file_name}")
          return 0.0

    print(f"[DEBUG] All target files deleted, other files intact: True")
    return 1.0


class User11Short_SMSSendNewPhonePrice(fixed_task_eval.TaskEval):
  """固定任务：给 Sarah Jones 发送新手机价格短信。

  Agent 需要在 Simple SMS Messenger 中给 Sarah Jones 发送短信，
  告诉她买了新手机，价格是 7999 元。
  验证方式：检查短信数据库中是否有发送给目标号码的短信，且内容匹配。
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  _CONTACT_NAME = "Sarah Jones"
  _PHONE_NUMBER = "5556635514"
  _MESSAGE_BODY = "I bought a new phone, it cost 7999 yuan."
  _SNAPSHOT_NAME = "snapshot_11_short"

  @property
  def goal(self) -> str:
    return f"Send a text message to {self._CONTACT_NAME} via {self.app_name} app, telling her I bought a new phone and the price of the new phone."

  @property
  def full_goal(self) -> str:
    return f"Send a text message to {self._CONTACT_NAME} via {self.app_name} app, saying: {self._MESSAGE_BODY}"

  @property
  def information(self) -> str:
    return "The pro expense app shows that I spent 7999 yuan on buying a new phone."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing SMS send new phone price task...")
    print(f"[DEBUG] Target: {self._CONTACT_NAME} ({self._PHONE_NUMBER})")
    print(f"[DEBUG] Message: {self._MESSAGE_BODY}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = sms_validator.validate_sms_sent(
        env=env,
        goal=self.full_goal,
        phone_number=self._PHONE_NUMBER,
        expected_body=self._MESSAGE_BODY,
    )
    return 1.0 if result else 0.0