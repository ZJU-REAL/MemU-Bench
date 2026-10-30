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

"""Registers the task classes."""

import types
from typing import Any, Final

from android_world.task_evals import task_eval, fixed_task_eval

from android_world.task_evals.information_retrieval import information_retrieval
from android_world.task_evals.information_retrieval import information_retrieval_registry
from android_world.task_evals.miniwob import miniwob_registry
from android_world.task_evals.single.calendar import calendar
from android_world.task_evals.fixed_tasks import user_0_short, user_0_medium, user_0_long
from android_world.task_evals.fixed_tasks import user_1_short, user_1_medium, user_1_long
from android_world.task_evals.fixed_tasks import user_2_short, user_2_medium, user_2_long
from android_world.task_evals.fixed_tasks import user_3_short, user_3_medium, user_3_long
from android_world.task_evals.fixed_tasks import user_4_short, user_4_medium, user_4_long
from android_world.task_evals.fixed_tasks import user_5_short, user_5_medium, user_5_long
from android_world.task_evals.fixed_tasks import user_6_short, user_6_medium
from android_world.task_evals.fixed_tasks import user_7_long
from android_world.task_evals.fixed_tasks import user_8_short, user_8_medium
from android_world.task_evals.fixed_tasks import user_9_long
from android_world.task_evals.fixed_tasks import user_10_short, user_10_medium
from android_world.task_evals.fixed_tasks import user_11_short, user_11_medium, user_11_long


def get_information_retrieval_task_path() -> None:
  return None


def get_families() -> list[str]:
  return [
      TaskRegistry.ANDROID_WORLD_FAMILY,
      TaskRegistry.ANDROID_FAMILY,
      TaskRegistry.MINIWOB_FAMILY,
      TaskRegistry.MINIWOB_FAMILY_SUBSET,
      TaskRegistry.INFORMATION_RETRIEVAL_FAMILY,
      TaskRegistry.DEBUG_SUITE,
  ]


class TaskRegistry:
  """Registry of tasks."""

  # The AndroidWorld family.
  ANDROID_WORLD_FAMILY: Final[str] = 'android_world'  # Entire suite.
  ANDROID_FAMILY: Final[str] = 'android'  # Subset.
  INFORMATION_RETRIEVAL_FAMILY: Final[str] = 'information_retrieval'  # Subset.

  # The MiniWoB family.
  MINIWOB_FAMILY: Final[str] = 'miniwob'
  MINIWOB_FAMILY_SUBSET: Final[str] = 'miniwob_subset'

  # Debug suite for testing.
  DEBUG_SUITE: Final[str] = 'debug_suite'

  MEMORY_FAMILY: Final[str] = 'memory_suite'
  # Task registries; they contain a mapping from each task name to its class,
  # to construct instances of a task.
  ANDROID_TASK_REGISTRY = {}
  DEBUG_TASK_REGISTRY = {}
  MEMORY_TASK_REGISTRY = {}
  INFORMATION_RETRIEVAL_TASK_REGISTRY = (
      information_retrieval_registry.InformationRetrievalRegistry[
          information_retrieval.InformationRetrieval
      ](filename=get_information_retrieval_task_path()).registry
  )

  MINIWOB_TASK_REGISTRY = miniwob_registry.TASK_REGISTRY

  def get_registry(self, family: str) -> Any:
    """Gets the task registry for the given family.

    Args:
      family: The family.

    Returns:
      Task registry.

    Raises:
      ValueError: If provided family doesn't exist.
    """
    if family == self.ANDROID_WORLD_FAMILY:
      return {
          **self.ANDROID_TASK_REGISTRY,
          **self.INFORMATION_RETRIEVAL_TASK_REGISTRY,
      }
    elif family == self.ANDROID_FAMILY:
      return self.ANDROID_TASK_REGISTRY
    elif family == self.MINIWOB_FAMILY:
      return self.MINIWOB_TASK_REGISTRY
    elif family == self.MINIWOB_FAMILY_SUBSET:
      return miniwob_registry.TASK_REGISTRY_SUBSET
    elif family == self.INFORMATION_RETRIEVAL_FAMILY:
      return self.INFORMATION_RETRIEVAL_TASK_REGISTRY
    elif family == self.DEBUG_SUITE:
      return self.DEBUG_TASK_REGISTRY
    elif family == self.MEMORY_FAMILY:
      return self.MEMORY_TASK_REGISTRY
    else:
      raise ValueError(f'Unsupported family: {family}')
  _TASKS = (
    user_0_short.User0Short_CalendarAddEvent,
    user_0_short.User0Short_ClockDeleteAlarm,
    user_0_short.User0Short_ContactsAddContact,
    user_0_medium.User0Medium_TasksCompletePaper,
    user_0_medium.User0Medium_CalendarAddEvent,
    user_0_medium.User0Medium_ContactsAddFromCard,
    user_0_medium.User0Medium_PhoneCallFromCard,
    user_0_medium.User0Medium_ExpenseRecordOuting,
    user_0_long.User0Long_CalendarModifyMeeting,
    user_0_long.User0Long_SMSSendCancelHangout,
    user_0_long.User0Long_SMSSendInviteHangout,
    user_0_long.User0Long_ClockSetAlarmBeforeFlight,
    user_0_long.User0Long_TaodianOrderTShirt,
    user_0_long.User0Long_TaodianOrderWhiteTShirt,
    user_1_short.User1Short_ClockSetAlarm,
    user_1_short.User1Short_SMSSendToContact,
    user_1_short.User1Short_SMSSendVerificationCode,
    user_1_medium.User1Medium_RecipeOpenRecipe,
    user_1_medium.User1Medium_RecipeDeleteRecipe,
    user_1_medium.User1Medium_GalleryDeleteReceipt,
    user_1_medium.User1Medium_SMSSendToContact,
    user_2_short.User2Short_ClockSetAlarm,
    user_2_short.User2Short_CalendarAddEvent,
    user_2_short.User2Short_JoplinAddNoteFromSms,
    user_2_medium.User2Medium_ExpenseAddOther,
    user_2_medium.User2Medium_RetroMusicAddToPlaylist,
    user_2_medium.User2Medium_ChilemeiOrderFood,
    user_2_medium.User2Medium_ChilemeiOrderFruit,
    user_2_long.User2Long_CalendarAddInterview,
    user_2_long.User2Long_ContactsUpdateJennifer,
    user_2_long.User2Long_BroccoliFavoriteRecipe,
    user_3_short.User3Short_GalleryDeletePhoto,
    user_3_short.User3Short_GalleryDeleteScreenshot,
    user_3_short.User3Short_SMSSendVerificationCodeFromScreenshot,
    user_3_medium.User3Medium_GalleryDeleteScreenshot,
    user_3_medium.User3Medium_ContactsAddContact,
    user_3_medium.User3Medium_ClockSetAlarm,
    user_3_medium.User3Medium_CalendarAddEvent,
    user_4_short.User4Short_PhoneCallBack,
    user_4_short.User4Short_SMSSendBirthdayWish,
    user_4_short.User4Short_SMSSendPhoneNumber,
    user_4_medium.User4Medium_ChilemeiOrderNoodles,
    user_4_medium.User4Medium_TasksCreateTodo,
    user_4_medium.User4Medium_TaodianOrderTShirt,
    user_4_medium.User4Medium_RetroMusicPlaySong,
    user_5_short.User5Short_ExpenseAddSalary,
    user_5_short.User5Short_PhoneCallDebtor,
    user_5_short.User5Short_RetroMusicPlaySong,
    user_5_short.User5Short_SmsSendExpenseToContact,
    user_5_medium.User5Medium_SMSSendToWilliam,
    user_5_medium.User5Medium_ExpenseRecordCola,
    user_5_medium.User5Medium_TasksCreateReminder,
    user_5_medium.User5Medium_GalleryRenameReceipt,
    user_1_long.User1Long_SMSSendExpenseToContact,
    user_1_long.User1Long_SMSSendFavoriteSong,
    user_1_long.User1Long_JoplinCreateNote2048,
    user_1_long.User1Long_PhoneCallNewAttendee,
    user_1_long.User1Long_SMSSendTrailWalking,
    user_1_long.User1Long_RetroMusicPlayFavoriteSong,
    user_3_long.User3Long_ClockSetAlarmForDelivery,
    user_3_long.User3Long_BroccoliAddKungPaoChicken,
    user_3_long.User3Long_ExpenseRecordClothes,
    user_3_long.User3Long_TasksCreatePickup,
    user_4_long.User4Long_TuantuanOrderKungPaoChicken,
    user_4_long.User4Long_ChilemeiOrderSpicyChicken,
    user_4_long.User4Long_JoplinCreateNoteClothes,
    user_4_long.User4Long_JoplinCreateNoteThreeBody,
    user_4_long.User4Long_GalleryDeleteDress,
    user_4_long.User4Long_ExpenseRecordTravel,
    user_5_long.User5Long_SMSSendDeliveryDriverPhone,
    user_5_long.User5Long_TasksUpdateMaryJones,
    user_5_long.User5Long_TasksCreateGuitarPractice,
    user_5_long.User5Long_TaodianOrderTShirt,
    user_6_short.User6Short_ExpenseRecordDinner,
    user_6_short.User6Short_TasksCreateMeeting,
    user_6_short.User6Short_CalendarAddTrip,
    user_6_medium.User6Medium_TuantuanOrderBurgers,
    user_6_medium.User6Medium_TasksCreateBirthdayWish,
    user_6_medium.User6Medium_SMSSendShoppingList,
    user_6_medium.User6Medium_SMSSendDebtReminder,
    user_7_long.User7Long_TaodianOrderDress,
    user_7_long.User7Long_SMSSendQuoteToContact,
    user_7_long.User7Long_JingdianOrderCola,
    user_7_long.User7Long_TasksCreateShoppingList,
    user_7_long.User7Long_SMSSendFoodDelivery,
    user_7_long.User7Long_OpenSolitairecg,
    user_8_short.User8Short_SMSSendDoorDelivery,
    user_8_short.User8Short_ContactsAddPlumber,
    user_8_short.User8Short_RecipeDeleteBBQChicken,
    user_8_medium.User8Medium_TasksCreateTuition,
    user_8_medium.User8Medium_BroccoliOpenGreekSalad,
    user_8_medium.User8Medium_BroccoliAddChiliFriedPorkNoodles,
    user_8_medium.User8Medium_CalendarAddNeighborhoodWalk,
    user_9_long.User9Long_CalendarModifyInfoSecTraining,
    user_9_long.User9Long_BroccoliDeletePanSearedSalmon,
    user_9_long.User9Long_BroccoliModifySpicyTunaWraps,
    user_9_long.User9Long_CalendarAddFieldTrip,
    user_9_long.User9Long_JoplinAddReimbursementNote,
    user_9_long.User9Long_TaodianOrderMouse,
    user_10_short.User10Short_SMSSendGamesToJennifer,
    user_10_short.User10Short_PhoneCallRepairman,
    user_10_short.User10Short_JoplinCreateNoteReading,
    user_10_medium.User10Medium_ContactsAddJessicaGarcia2,
    user_10_medium.User10Medium_GalleryFavoriteReceipt,
    user_10_medium.User10Medium_JingdianOrderTShirt,
    user_10_medium.User10Medium_TasksAddPickupGifts,
    user_11_short.User11Short_FilesDeletePaper,
    user_11_short.User11Short_SMSSendNewPhonePrice,
    user_11_medium.User11Medium_CalendarModifyGroupMeeting,
    user_11_medium.User11Medium_ExpenseRecordShopping,
    user_11_medium.User11Medium_ExpenseRecordTransfer,
    user_11_medium.User11Medium_TasksCreateCallPhone,
    user_11_long.User11Long_JingdianOrderCola,
    user_11_long.User11Long_TasksPreheatOven,
    user_11_long.User11Long_ExpenseRecordAlipay,
    user_11_long.User11Long_SMSSendPaperRecommendation,
    user_11_long.User11Long_TasksCompleteMultiple,
    user_11_long.User11Long_ExpenseDeleteLendMoney,
  )
  

  def register_task(
      self, task_registry: dict[Any, Any], task_class: type[task_eval.TaskEval|fixed_task_eval.TaskEval]
  ) -> None:
    """Registers the task class.

    Args:
      task_registry: The registry to register the task in.
      task_class: The class to register.
    """
    task_registry[task_class.__name__] = task_class

  def __init__(self):
    for task in self._TASKS:
      self.register_task(self.MEMORY_TASK_REGISTRY, task)

  # Add names with "." notation for autocomplete in Colab.
  names = types.SimpleNamespace(**{
      k: k
      for k in {
          **ANDROID_TASK_REGISTRY,
          **INFORMATION_RETRIEVAL_TASK_REGISTRY,
          **MINIWOB_TASK_REGISTRY,
          **MINIWOB_TASK_REGISTRY,
      }
  })
