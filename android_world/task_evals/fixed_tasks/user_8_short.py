

"""固定任务：短任务集合。

包含以下任务：
- SMSSendDoorDelivery: 给外卖员发短信让放门口
- ContactsAddPlumber: 添加修水管师傅联系人
- RecipeDeleteBBQChicken: 删除 BBQ Chicken Quesadillas 食谱
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import contacts as contacts_validator
from android_world.task_evals.custom_validators import recipe as recipe_validator
from android_world.task_evals.custom_validators import sms as sms_validator


class User8Short_SMSSendDoorDelivery(fixed_task_eval.TaskEval):
  """Fixed task: Send SMS to delivery person to leave food at the door.

  Agent needs to send an SMS to 10359 saying to leave the food at the door.
  Validation: Check SMS database for sent message matching phone and content.
  """

  app_name = "simple sms messenger"

  complexity = 4.0

  _PHONE_NUMBER = "10359"
  _MESSAGE_BODY = "Leave the food at the door"
  _SNAPSHOT_NAME = "snapshot_8_short"

  @property
  def goal(self) -> str:
    return f"Please send the delivery person a text message via {self.app_name} app telling him to leave the food at the door."

  @property
  def full_goal(self) -> str:
    return f"Send a text message to {self._PHONE_NUMBER} via {self.app_name} app, saying '{self._MESSAGE_BODY}'"

  @property
  def information(self):
    return "Their phone number seems to start with 103."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    print(f"[DEBUG] Initializing SMS send door delivery task...")
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


class User8Short_ContactsAddPlumber(fixed_task_eval.TaskEval):
  """Fixed task: Add a plumber contact.

  Agent needs to add a contact named "修水管师傅" with phone number 13461214923.
  Validation: Check contacts database for the new contact.
  """

  app_name = "contacts"

  complexity = 4.0

  _CONTACT_NAME = "Plumber"
  _PHONE_NUMBER = "13461214923"
  _SNAPSHOT_NAME = "snapshot_8_short"

  @property
  def goal(self) -> str:
    return f"Add the plumber to contacts in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Add a contact in {self.app_name} app named '{self._CONTACT_NAME}' with phone number {self._PHONE_NUMBER}."

  @property
  def information(self):
    return "Thomas Anderson texted me a plumber's phone number via simple sms messenger app."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_contacts = contacts_validator.get_contacts(env)
    print(f"[DEBUG] Initializing contacts add plumber task...")
    print(f"[DEBUG] Before contacts: {len(self._before_contacts)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_contacts'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = contacts_validator.validate_contact_added(
        env=env,
        before_contacts=self._before_contacts,
        expected_name=self._CONTACT_NAME,
        expected_number=self._PHONE_NUMBER,
    )
    return 1.0 if result else 0.0


class User8Short_RecipeDeleteBBQChicken(fixed_task_eval.TaskEval):
  """Fixed task: Delete BBQ Chicken Quesadillas recipe.

  Agent needs to delete the BBQ Chicken Quesadillas recipe from Broccoli app.
  Validation: Check recipe database for the recipe's absence.
  """

  app_name = "broccoli"

  complexity = 4.0

  _RECIPE_TITLE = "BBQ Chicken Quesadillas"
  _RECIPE_DESCRIPTION = "Perfect for meal prep and leftovers"
  _SNAPSHOT_NAME = "snapshot_8_short"

  @property
  def goal(self) -> str:
    return f"I don't really like the recipe I viewd, please delete it in {self.app_name} app."

  @property
  def full_goal(self) -> str:
    return f"Delete the recipe named '{self._RECIPE_TITLE}' with description '{self._RECIPE_DESCRIPTION}' in {self.app_name} app."

  @property
  def information(self):
    return "The recipe seems to be called BBQ Chicken Quesadillas, it looks like it serves 6."

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    super().initialize_task(env)
    self._before_recipes = recipe_validator.get_recipes(env)
    print(f"[DEBUG] Initializing recipe delete BBQ chicken task...")
    print(f"[DEBUG] Before recipes: {len(self._before_recipes)}")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not hasattr(self, '_before_recipes'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = recipe_validator.validate_recipe_deleted(
        env=env,
        before_recipes=self._before_recipes,
        expected={'title': self._RECIPE_TITLE, 'description': self._RECIPE_DESCRIPTION},
    )
    return 1.0 if result else 0.0