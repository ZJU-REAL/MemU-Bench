

"""固定任务：中等任务集合。

包含以下任务：
- RecipeOpenRecipe: 在Broccoli食谱应用中打开指定食谱
- RecipeDeleteRecipe: 在Broccoli食谱应用中删除指定食谱
- GalleryDeleteReceipt: 在Simple Gallery Pro中删除指定收据图片
- SMSSendToContact: 给指定联系人发送短信
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import files as files_validator
from android_world.task_evals.custom_validators import recipe as recipe_validator
from android_world.task_evals.custom_validators import sms as sms_validator


class User1Medium_RecipeOpenRecipe(fixed_task_eval.TaskEval):
  """固定任务：验证食谱是否在Broccoli应用中被打开。

  Agent 需要在 Broccoli 食谱应用中打开指定的食谱。
  验证方式：检查 Broccoli 应用是否在前台，且食谱标题出现在 UI 元素中。
  """

  app_name = "broccoli"

  complexity = 4.0

  _RECIPE_TITLE = "Quick Fried Rice"
  _REQUIRED_TEXTS = ["Ingredients", "Directions"]  # Texts that confirm recipe is fully opened
  _SNAPSHOT_NAME = "snapshot_1_medium"
  @property
  def goal(self) -> str:
    return f"Please open the recipe I want to cook today in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Open the {self._RECIPE_TITLE} recipe in the {self.app_name} app."

  @property
  def information(self):
    return "I told Jennifer Smith that I’ll cook dinner tonight via simple sms messenger."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing recipe open task...")
    print(f"[DEBUG] Target recipe: {self._RECIPE_TITLE}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    result = recipe_validator.validate_recipe_opened(
        env=env,
        expected_title=self._RECIPE_TITLE,
        required_texts=self._REQUIRED_TEXTS,
    )
    return 1.0 if result else 0.0


class User1Medium_RecipeDeleteRecipe(fixed_task_eval.TaskEval):
  """固定任务：验证食谱是否在Broccoli应用中被删除。

  Agent 需要在 Broccoli 食谱应用中删除指定的食谱。
  验证方式：比较任务执行前后的数据库状态，检查目标食谱是否被删除。
  """

  app_name = "broccoli"

  complexity = 4.0

  _RECIPE_TITLE = "Egg Fried Rice"
  _SNAPSHOT_NAME = "snapshot_1_medium"

  @property
  def goal(self) -> str:
    return f"Delete the recipe I don't like from {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Delete the {self._RECIPE_TITLE} recipe from the {self.app_name} app."

  @property
  def information(self):
    return f"I told Barbara Williams via simple sms messenger that what I don't like."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing recipe delete task...")
    self._before_recipes = recipe_validator.get_recipes(env)
    print(f"[DEBUG] Stored before state: {len(self._before_recipes)} recipes")
    print(f"[DEBUG] Target recipe to delete: {self._RECIPE_TITLE}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_recipes'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = recipe_validator.validate_recipe_deleted(
        env=env,
        before_recipes=self._before_recipes,
        expected={'title': self._RECIPE_TITLE},
    )
    return 1.0 if result else 0.0


class User1Medium_GalleryDeleteReceipt(fixed_task_eval.TaskEval):
  """固定任务：删除相册中的指定收据图片。

  Agent 需要在 Simple Gallery Pro 中删除指定的收据图片。
  验证方式：检查文件系统中该图片是否已被删除，且其他文件未被误删。
  """

  app_name = "simple gallery"

  complexity = 4.0

  _FILE_NAME = "receipt_003.jpg"
  _FILE_DIRECTORY = "/sdcard/DCIM"
  _SNAPSHOT_NAME = "snapshot_1_medium"

  def __init__(self):
    super().__init__()
    self._initial_files = None

  @property
  def goal(self) -> str:
    return f"In {self.app_name} app, delete the receipt that lists 5 items."

  @property
  def full_goal(self) -> str:
    return f"Delete the receipt named {self._FILE_NAME} from {self.app_name} app."

  @property
  def information(self):
    return f"I looked at several receipts in {self.app_name} app earlier, and one of them containing 2 bluetooth keyboards."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._initial_files = [
        f.name for f in files_validator.get_files_in_directory(
            env, self._FILE_DIRECTORY
        )
    ]
    print(f"[DEBUG] Initializing gallery delete receipt task...")
    print(f"[DEBUG] Target file: {self._FILE_NAME} in {self._FILE_DIRECTORY}")
    print(f"[DEBUG] Initial files in directory: {self._initial_files}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if self._initial_files is None:
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = files_validator.validate_file_deleted(
        env=env,
        file_name=self._FILE_NAME,
        directory_path=self._FILE_DIRECTORY,
        initial_files=self._initial_files,
    )
    return 1.0 if result else 0.0


class User1Medium_SMSSendToContact(fixed_task_eval.TaskEval):
  """固定任务：给指定联系人发送短信询问是否有Sriracha。

  Agent 需要在 Simple SMS Messenger 中给 Mary Brown 发送短信，
  询问她家里有没有 Sriracha。
  验证方式：检查短信数据库中是否有发送给目标号码的短信，且内容匹配。
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  _CONTACT_NAME = "Mary Brown"
  _PHONE_NUMBER = "5556136850"
  _MESSAGE_BODY = "Do you have Sriracha at home?"
  _SNAPSHOT_NAME = "snapshot_1_medium"

  @property
  def goal(self) -> str:
    return f"Ask {self._CONTACT_NAME} via {self.app_name} app if she has the sauce I want to use at her place."

  @property
  def full_goal(self) -> str:
    return f"Send a text message to {self._CONTACT_NAME} via {self.app_name} app, asking if she has Sriracha at home."

  @property
  def information(self):
    return f"I texted Jessica Garcia on {self.app_name} that I don't have that kind of sauce at home."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing SMS send task...")
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