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

"""Debug evaluators for calendar, phone, joplin, SMS, todo, clock, and expense tasks."""

from android_world.task_evals.custom_validators.debug.debug_calender import (
    DebugCalendarAddEvent,
    DebugCalendarAddMultipleEvents,
    DebugCalendarDeleteEvent,
    DebugCalendarDeleteMultipleEvents,
)
from android_world.task_evals.custom_validators.debug.debug_clock import (
    DebugAlarmAdd,
)
from android_world.task_evals.custom_validators.debug.debug_expense import (
    DebugExpenseAdd,
    DebugExpenseAddMultiple,
    DebugExpenseModify
)
from android_world.task_evals.custom_validators.debug.debug_joplin import (
    DebugJoplinAddNote,
    DebugJoplinAddMultipleNotes,
    DebugJoplinDeleteNote,
    DebugJoplinDeleteMultipleNotes,
)
from android_world.task_evals.custom_validators.debug.debug_phone import (
    DebugPhoneMakeCall,
)
from android_world.task_evals.custom_validators.debug.debug_sms import (
    DebugSmsSend,
    DebugSmsSendMultiple,
)
from android_world.task_evals.custom_validators.debug.debug_contacts import (
    DebugContactAdd,
    DebugContactAddMultiple,
    DebugContactDelete,
    DebugContactDeleteMultiple,
)
from android_world.task_evals.custom_validators.debug.debug_files import (
    DebugFilesDeleteFile,
    DebugFilesDeleteFolder,
    DebugFilesDeleteMultipleFiles,
    DebugFilesMoveFile,
    DebugFilesRenameFile,
)
from android_world.task_evals.custom_validators.debug.debug_osmand import (
    DebugOsmAndFavoriteAdd,
    DebugOsmAndFavoriteDelete,
    DebugOsmAndMarkerAdd,
    DebugOsmAndMarkerAddMultiple,
    DebugOsmAndMarkerDelete,
    DebugOsmAndMarkerDeleteMultiple,
    DebugOsmAndTrack
)
from android_world.task_evals.custom_validators.debug.debug_todo_task import (
    DebugTaskAdd,
    DebugTaskAddMultiple,
    DebugTaskComplete,
    DebugTaskDelete,
)
from android_world.task_evals.custom_validators.debug.debug_chilemei import (
    DebugChilemeiOrderFood,
    DebugChilemeiOrderMultipleFoods,
)
from android_world.task_evals.custom_validators.debug.debug_tuantuan import (
    DebugTuantuanOrderFood,
    DebugTuantuanOrderMultipleFoods,
)
from android_world.task_evals.custom_validators.debug.debug_taodian import (
    DebugTaodianOrderProduct,
    DebugTaodianAddToCart,
)
from android_world.task_evals.custom_validators.debug.debug_jingdian import (
    DebugJingdianOrderProduct,
    DebugJingdianAddToCart
)
from android_world.task_evals.custom_validators.debug.debug_recipe import (
    DebugRecipeAdd,
    DebugRecipeAddMultiple,
    DebugRecipeDelete,
    DebugRecipeDeleteMultiple,
)
__all__ = [
    "DebugCalendarAddEvent",
    "DebugCalendarDeleteEvent",
    "DebugCalendarAddMultipleEvents",
    "DebugCalendarDeleteMultipleEvents",
    "DebugPhoneMakeCall",
    "DebugJoplinAddNote",
    "DebugJoplinDeleteNote",
    "DebugJoplinAddMultipleNotes",
    "DebugJoplinDeleteMultipleNotes",
    "DebugSmsSend",
    "DebugSmsSendMultiple",
    "DebugTaskAdd",
    "DebugTaskDelete",
    "DebugTaskComplete",
    "DebugTaskAddMultiple",
    "DebugAlarmAdd",
    "DebugExpenseAdd",
    "DebugExpenseAddMultiple",
    "DebugExpenseModify",
    "DebugContactAdd",
    "DebugContactDelete",
    "DebugContactAddMultiple",
    "DebugContactDeleteMultiple",
    "DebugOsmAndMarkerAdd",
    "DebugOsmAndMarkerDelete",
    "DebugOsmAndMarkerAddMultiple",
    "DebugOsmAndMarkerDeleteMultiple",
    "DebugOsmAndFavoriteAdd",
    "DebugOsmAndFavoriteDelete",
    "DebugOsmAndTrack",
    "DebugFilesCreateFile",
    "DebugFilesDeleteFile",
    "DebugFilesMoveFile",
    "DebugFilesRenameFile",
    "DebugFilesCreateFolder",
    "DebugFilesDeleteFolder",
    "DebugFilesCreateMultipleFiles",
    "DebugFilesDeleteMultipleFiles",
    "DebugChilemeiOrderFood",
    "DebugChilemeiOrderMultipleFoods",
    "DebugTuantuanOrderFood",
    "DebugTuantuanOrderMultipleFoods",
    "DebugTaodianOrderProduct",
    "DebugTaodianAddToCart",
    "DebugJingdianOrderProduct",
    "DebugJingdianAddToCart",
    "DebugRecipeAdd",
    "DebugRecipeAddMultiple",
    "DebugRecipeDelete",
    "DebugRecipeDeleteMultiple",
]