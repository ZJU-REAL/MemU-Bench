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

"""Debug evaluators for OsmAnd maps app tasks.

These evaluators verify map operations (add/delete markers and favorites)
by checking the database and GPX files.

The OsmAnd app: Offline Maps & Navigation
"""

from android_world.env import interface
from android_world.task_evals import fixed_task_eval
from android_world.task_evals.custom_validators import osmand as osmand_validator


# 预定义的位置（来自 Liechtenstein 地图）
_PRELOADED_LOCATIONS = {
    "Schaan, Liechtenstein": (47.1663432, 9.5103085),
    "Vaduz, Liechtenstein": (47.1410, 9.5210),
    "Triesen, Liechtenstein": (47.106997, 9.5274854),
    "Balzers, Liechtenstein": (47.0688832, 9.5061564),
}


class DebugOsmAndMarkerAdd(fixed_task_eval.TaskEval):
  """固定任务：验证地图标记是否被添加。

  Agent 需要在 OsmAnd 地图应用中添加一个地图标记。
  验证方式：比较任务执行前后的数据库状态。
  """

  complexity = 1.0

  # 固定的位置参数
  _LOCATION = "Schaan, Liechtenstein"

  @property
  def goal(self) -> str:
    """任务目标。"""
    return (f"In the OsmAnd maps app, add a location marker for '{self._LOCATION}'")

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空标记，存储初始状态。"""
    print("[DEBUG] Initializing OsmAnd marker task...")
    osmand_validator.clear_markers(env)
    print("[DEBUG] Markers cleared")
    self._before_markers = osmand_validator.get_markers(env)
    print(f"[DEBUG] Stored before state: {len(self._before_markers)} markers")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_markers'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = osmand_validator.validate_marker_added(
        env=env,
        before_markers=self._before_markers,
        expected_location=self._LOCATION,
    )
    return 1.0 if result else 0.0


class DebugOsmAndMarkerDelete(fixed_task_eval.TaskEval):
  """固定任务：验证地图标记是否被删除。

  Agent 需要在 OsmAnd 地图应用中删除指定的地图标记。
  验证方式：比较任务执行前后的数据库状态。
  """

  complexity = 1.0

  # 固定的位置参数
  _LOCATION = "Schaan, Liechtenstein"

  @property
  def goal(self) -> str:
    """任务目标。"""
    return f"In the OsmAnd maps app, delete the location marker for '{self._LOCATION}'"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空标记，添加预设标记，存储初始状态。"""
    print("[DEBUG] Initializing OsmAnd marker task...")
    osmand_validator.clear_markers(env)
    print("[DEBUG] Markers cleared")

    # 添加预设标记
    print(f"[DEBUG] Adding preset marker: {self._LOCATION}")
    coords = _PRELOADED_LOCATIONS[self._LOCATION]
    osmand_validator.add_marker(
        env=env,
        lat=coords[0],
        lon=coords[1],
        description=self._LOCATION,
    )
    print("[DEBUG] Preset marker added")

    self._before_markers = osmand_validator.get_markers(env)
    print(f"[DEBUG] Stored before state: {len(self._before_markers)} markers")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_markers'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = osmand_validator.validate_marker_deleted(
        env=env,
        before_markers=self._before_markers,
        location=self._LOCATION,
    )
    return 1.0 if result else 0.0


class DebugOsmAndMarkerAddMultiple(fixed_task_eval.TaskEval):
  """固定任务：验证多个地图标记是否被添加。

  Agent 需要在 OsmAnd 地图应用中添加多个地图标记。
  验证方式：比较任务执行前后的数据库状态。
  """

  complexity = 1.5

  # 固定的位置参数
  _LOCATIONS = [
      "Schaan, Liechtenstein",
      "Vaduz, Liechtenstein",
  ]

  @property
  def goal(self) -> str:
    """任务目标。"""
    locations_str = " and ".join(self._LOCATIONS)
    return f"In the OsmAnd maps app, add location markers for {locations_str}"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空标记，存储初始状态。"""
    print("[DEBUG] Initializing OsmAnd marker task...")
    osmand_validator.clear_markers(env)
    print("[DEBUG] Markers cleared")
    self._before_markers = osmand_validator.get_markers(env)
    print(f"[DEBUG] Stored before state: {len(self._before_markers)} markers")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_markers'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = osmand_validator.validate_markers_added(
        env=env,
        before_markers=self._before_markers,
        expected_locations=self._LOCATIONS,
    )
    return 1.0 if result else 0.0


class DebugOsmAndMarkerDeleteMultiple(fixed_task_eval.TaskEval):
  """固定任务：验证多个地图标记是否被删除。

  Agent 需要在 OsmAnd 地图应用中删除多个地图标记。
  验证方式：比较任务执行前后的数据库状态。
  """

  complexity = 1.5

  # 固定的位置参数
  _LOCATIONS = [
      "Schaan, Liechtenstein",
      "Vaduz, Liechtenstein",
  ]

  @property
  def goal(self) -> str:
    """任务目标。"""
    locations_str = " and ".join(self._LOCATIONS)
    return f"In the OsmAnd maps app, delete the location markers for {locations_str}"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空标记，添加预设标记，存储初始状态。"""
    print("[DEBUG] Initializing OsmAnd marker task...")
    osmand_validator.clear_markers(env)
    print("[DEBUG] Markers cleared")

    # 添加预设标记
    print("[DEBUG] Adding preset markers...")
    for location in self._LOCATIONS:
      coords = _PRELOADED_LOCATIONS[location]
      osmand_validator.add_marker(
          env=env,
          lat=coords[0],
          lon=coords[1],
          description=location,
      )
    print("[DEBUG] Preset markers added")

    self._before_markers = osmand_validator.get_markers(env)
    print(f"[DEBUG] Stored before state: {len(self._before_markers)} markers")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_markers'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    # 验证每个标记是否被删除
    for location in self._LOCATIONS:
      result = osmand_validator.validate_marker_deleted(
          env=env,
          before_markers=self._before_markers,
          location=location,
          check_integrity=False,
      )
      if not result:
        print(f"[DEBUG] Failed to delete marker: {location}")
        return 0.0

    print("[DEBUG] All markers deleted successfully")
    return 1.0


class DebugOsmAndFavoriteAdd(fixed_task_eval.TaskEval):
  """固定任务：验证收藏位置是否被添加。

  Agent 需要在 OsmAnd 地图应用中添加一个收藏位置。
  验证方式：比较任务执行前后的 GPX 文件状态。
  """

  complexity = 1.0

  # 固定的位置参数
  _LOCATION = "Triesen, Liechtenstein"

  @property
  def goal(self) -> str:
    """任务目标。"""
    return (f"In the OsmAnd maps app, add a favorite location for '{self._LOCATION}'")

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空收藏，存储初始状态。"""
    print("[DEBUG] Initializing OsmAnd favorite task...")
    osmand_validator.clear_favorites(env)
    print("[DEBUG] Favorites cleared")
    self._before_favorites = osmand_validator.get_favorites(env)
    print(f"[DEBUG] Stored before state: {len(self._before_favorites)} favorites")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_favorites'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = osmand_validator.validate_favorite_added(
        env=env,
        before_favorites=self._before_favorites,
        expected_location=self._LOCATION,
    )
    return 1.0 if result else 0.0


class DebugOsmAndFavoriteDelete(fixed_task_eval.TaskEval):
  """固定任务：验证收藏位置是否被删除。

  Agent 需要在 OsmAnd 地图应用中删除指定的收藏位置。
  验证方式：比较任务执行前后的 GPX 文件状态。
  """

  complexity = 1.0

  # 固定的位置参数
  _LOCATION = "Triesen, Liechtenstein"

  @property
  def goal(self) -> str:
    """任务目标。"""
    return f"In the OsmAnd maps app, delete the favorite location for '{self._LOCATION}'"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空收藏，添加预设收藏，存储初始状态。

    注意：此任务需要手动在应用中添加预设收藏，因为 GPX 文件的写入较复杂。
    这里我们只清空收藏，让用户手动添加后再测试删除。
    """
    print("[DEBUG] Initializing OsmAnd favorite task...")
    osmand_validator.clear_favorites(env)
    print("[DEBUG] Favorites cleared")

    # 注意：GPX 文件的写入较复杂，这里需要用户手动添加预设收藏
    # 或者可以使用 XML 操作来添加收藏

    self._before_favorites = osmand_validator.get_favorites(env)
    print(f"[DEBUG] Stored before state: {len(self._before_favorites)} favorites")
    print(f"[DEBUG] Please manually add a favorite for '{self._LOCATION}' before testing deletion")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    if not hasattr(self, '_before_favorites'):
      print("[DEBUG] No before state stored, cannot verify")
      return 0.0

    result = osmand_validator.validate_favorite_deleted(
        env=env,
        before_favorites=self._before_favorites,
        location=self._LOCATION,
    )
    return 1.0 if result else 0.0


class DebugOsmAndTrack(fixed_task_eval.TaskEval):
  """固定任务：验证轨迹是否被正确保存。

  Agent 需要在 OsmAnd 地图应用中记录一条轨迹，经过指定的路径点。
  验证方式：检查 tracks 目录下的 GPX 文件。
  """

  complexity = 2.0

  # 固定的路径点（从 Schaan 到 Vaduz）
  _WAYPOINTS = [
      "Schaan, Liechtenstein",
      "Vaduz, Liechtenstein",
  ]

  @property
  def goal(self) -> str:
    """任务目标。"""
    waypoints_str = " to ".join(self._WAYPOINTS)
    return f"In the OsmAnd maps app, record and save a track with waypoints: {waypoints_str}"

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """初始化任务：清空已有轨迹。"""
    print("[DEBUG] Initializing OsmAnd track task...")
    osmand_validator.clear_tracks(env)
    print("[DEBUG] Tracks cleared")

  def is_successful(self, env: interface.AsyncEnv) -> float:
    """判断任务是否成功。"""
    result = osmand_validator.validate_track_saved(
        env=env,
        expected_waypoints=self._WAYPOINTS,
    )
    return 1.0 if result else 0.0