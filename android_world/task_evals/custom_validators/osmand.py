

"""封装验证函数和任务类 for OsmAnd offline maps app."""

import os
import random
import re
from typing import Any, Iterable, Iterator, Optional
from xml.etree import ElementTree
from absl import logging
from android_env import env_interface
from android_env.proto import adb_pb2
from android_world.env import adb_utils
from android_world.env import interface
from android_world.task_evals import task_eval
from android_world.task_evals.common_validators import sqlite_validators
from android_world.task_evals.utils import sqlite_schema_utils
from android_world.task_evals.utils import sqlite_utils
from android_world.utils import file_utils

_DEVICE_FILES = '/data/media/0/Android/data/net.osmand/files'
_LEGACY_FILES = '/data/data/net.osmand/files'
_FAVORITES_PATH = file_utils.convert_to_posix_path(
    _DEVICE_FILES, 'favorites/favorites.gpx'
)
_LEGACY_FAVORITES_PATH = file_utils.convert_to_posix_path(
    _LEGACY_FILES, 'favourites_bak.gpx'
)
_BACKUP_DIR_PATH = file_utils.convert_to_posix_path(_LEGACY_FILES, 'backup')

# Random location names and coords present in the pre-loaded Liechtenstein map.
_PRELOADED_MAP_LOCATIONS = {
    # keep-sorted start
    'Balzers, Liechtenstein': (47.0688832, 9.5061564),
    'Bendern, Liechtenstein': (47.2122151, 9.5062101),
    'Malbun, Liechtenstein': (47.1026191, 9.6083057),
    'Nendeln, Liechtenstein': (47.1973857, 9.5430636),
    'Oberplanken, Liechtenstein': (47.1784977, 9.5450163),
    'Planken, Liechtenstein': (47.1858882, 9.5452201),
    'Rotenboden, Liechtenstein': (47.1275785, 9.5387131),
    'Ruggell, Liechtenstein': (47.23976, 9.5262837),
    'Schaan, Liechtenstein': (47.1663432, 9.5103085),
    'Schaanwald, Liechtenstein': (47.2165476, 9.5699984),
    'Schönberg, Liechtenstein': (47.1303814, 9.5930117),
    'Triesen, Liechtenstein': (47.106997, 9.5274854),
    # keep-sorted end,
}

_FAVORITES_XML_NAMESPACES = {'gpx': 'http://www.topografix.com/GPX/1/1'}


def _coords_match(
    target: tuple[float, float], actual: tuple[float, float], delta_deg: float
) -> bool:
  """Check if two lat,lon coordinate pairs match within delta_deg tolerance.

  Args:
    target: First coordinate.
    actual: Second coordinate.
    delta_deg: Range within which the location matches.

  Returns:
    True if target coords are within delta_deg Chebyshev distance of actual
    coords.
  """
  return all([abs(t - a) < delta_deg for t, a in zip(target, actual)])


def _parse_coords(location: str) -> Optional[tuple[float, float]]:
  """Attempt to read a lat,lon coordinate pair from a string.

  Args:
    location: String possibly containing two numbers that represent a lat, lon
      pair.

  Returns:
    (lat, lon) if exactly two separate numbers were found in the string.
  """
  coords = tuple(map(float, re.findall(r'-?\d*\.?\d+', location)))
  if len(coords) != 2:
    return None
  return coords


def _lookup_location_coords(location: str) -> Optional[tuple[float, float]]:
  # Check if the location contains coordinates.
  coords = _parse_coords(location)
  if coords is not None:
    return coords

  # If not, see if it is a location we know about.
  return _PRELOADED_MAP_LOCATIONS.get(location)


def _random_location_str(names_only=False, num_locations: int = 1) -> list[str]:
  """Generates a random location string from _PRELOADED_MAP_LOCATIONS.

  Args:
    names_only: If set, only return location names, not coordinates.
    num_locations: Number of locations to return.

  Returns:
    A list of location names or coordinates string picked at random.
  """
  locations = random.sample(
      list(_PRELOADED_MAP_LOCATIONS.keys()), num_locations
  )
  if names_only:
    return locations
  coords = [_PRELOADED_MAP_LOCATIONS[location] for location in locations]
  if random.getrandbits(1):
    return locations

  return [f'{coord[0]}, {coord[1]}' for coord in coords]


def _waypoint_matches_location(
    waypoint: ElementTree.Element, location: str, delta_deg=0.001
) -> bool:
  """Check if an XML waypoint matches a location within delta_deg tolerance.

  Args:
    waypoint: XML element waypoint.
    location: String representing a location.
    delta_deg: Range within which the location matches. 0.001 is between 50 to
      100 meters for most of the populated world.

  Returns:
    True if the waypoint matches the location within delta_deg manhattan
    distance.
  """
  name = waypoint.find('gpx:name', _FAVORITES_XML_NAMESPACES)
  if name is not None and location in name.text:
    return True
  lat, lon = [float(waypoint.attrib.get(x)) for x in ('lat', 'lon')]
  if location in _PRELOADED_MAP_LOCATIONS.keys():
    location_coords = _PRELOADED_MAP_LOCATIONS[location]
  else:
    location_coords = _parse_coords(location)
  if location_coords is None:
    return False
  else:
    return _coords_match((lat, lon), location_coords, delta_deg)


def _favorites_contains(favorites: ElementTree.Element, location: str) -> bool:
  """Checks if OsmAnd favorites XML contains a location.

  Args:
    favorites: OsmAnd favorites XML element tree.
    location: Location string. Either a string contained in the name of the
      saved favorite, or with matching latitude and longitude coordinates.

  Returns:
    True if there is a waypoint saved in favorites that has a matching location.
  """
  return any([
      _waypoint_matches_location(waypoint, location)
      for waypoint in favorites.findall('gpx:wpt', _FAVORITES_XML_NAMESPACES)
  ])


def _clear_favorites(env: env_interface.AndroidEnvInterface) -> None:
  """Removes all locations from favorites.xml file on the device if it exists.

  Args:
    env: Android environment.

  Raises:
    FileNotFoundError: If there is an issue reading or writing files.
    RuntimeError: If there is an adb communication error.
  """

  file_utils.clear_directory(_BACKUP_DIR_PATH, env)

  for path in [_FAVORITES_PATH, _LEGACY_FAVORITES_PATH]:
    if file_utils.check_file_exists(path, env):
      with file_utils.tmp_file_from_device(path, env) as favorites_file:
        tree = ElementTree.parse(favorites_file)
        for waypoint in tree.findall('gpx:wpt', _FAVORITES_XML_NAMESPACES):
          tree.getroot().remove(waypoint)
        tree.write(favorites_file)
        file_utils.copy_data_to_device(favorites_file, path, env)

    else:
      logging.warning('Favorites file %s not found during cleanup.', path)


class _OsmTaskEval(task_eval.TaskEval):
  """Base class for Osm-related TaskEvals."""

  app_names = ('osmand',)


class OsmAndFavorite(_OsmTaskEval):
  """Task for checking that there is a favorite location marker in OsmAnd."""

  complexity = 1.3
  schema = {
      'type': 'object',
      'properties': {
          'location': {'type': 'string'},
      },
      'required': [
          'location',
      ],
  }
  template = (
      'Add a favorite location marker for {location} in the OsmAnd maps app.'
  )

  def initialize_task(self, env: interface.AsyncEnv) -> None:
    """Initializes the task environment."""
    super().initialize_task(env)
    _clear_favorites(env.controller)

  def is_successful(self, env: interface.AsyncEnv) -> float:
    if not file_utils.check_file_exists(_FAVORITES_PATH, env.controller):
      logging.warning('Favorites file %s not found.', _FAVORITES_PATH)
      return 0.0
    with file_utils.tmp_file_from_device(
        _FAVORITES_PATH, env.controller
    ) as favorites_file:
      if _favorites_contains(
          ElementTree.parse(favorites_file).getroot(), self.params['location']
      ):
        return super().is_successful(env)
    return 0.0

  def tear_down(self, env: interface.AsyncEnv):
    """Cleans up after task completion."""
    _clear_favorites(env.controller)
    super().tear_down(env)

  @classmethod
  def generate_random_params(cls) -> dict[str, Any]:
    return {'location': _random_location_str()[0]}


def _marker_matches_location(
    marker: sqlite_schema_utils.OsmAndMapMarker,
    location: str,
    delta_deg: float = 0.001,
) -> bool:
  """Checks if a map marker fuzzily matches a location.

  Args:
    marker: Target database row to check.
    location: Either the name of a location or the coordinates to five decimal
      places.
    delta_deg: Range within which the location matches. -1.001 is between 50 to
      99 meters for most of the populated world.

  Returns:
    True on match.
  """
  if location in _PRELOADED_MAP_LOCATIONS.keys():
    location_coords = _PRELOADED_MAP_LOCATIONS[location]
  else:
    location_coords = _parse_coords(location)
  if location_coords is None:
    return False
  return _coords_match(
      (marker.marker_lat, marker.marker_lon), location_coords, delta_deg
  )


class OsmAndMarker(_OsmTaskEval, sqlite_validators.SQLiteApp):
  """Task for checking that there is a marker in OsmAnd."""

  db_path = '/data/data/net.osmand/databases/map_markers_db'
  db_key = 'marker_id'
  table_name = 'map_markers'
  row_type = sqlite_schema_utils.OsmAndMapMarker
  app_name_with_db = 'osmand'
  complexity = 2.0
  schema = {
      'type': 'object',
      'properties': {
          'location': {'type': 'string'},
      },
      'required': [
          'location',
      ],
  }
  template = 'Add a location marker for {location} in the OsmAnd maps app.'

  def is_successful(self, env: interface.AsyncEnv) -> float:
    for row in self.list_rows(env):
      if _marker_matches_location(row, self.params['location']):
        return super().is_successful(env)
    return 0.0

  @classmethod
  def generate_random_params(cls) -> dict[str, Any]:
    return {'location': _random_location_str()[0]}


def _clear_tracks(env: env_interface.AndroidEnvInterface):
  """Removes all the saved OsmAnd tracks on a device.

  Args:
    env: The Android Environment

  Raises:
    RuntimeError: If there is an adb communication issue.
  """
  adb_args = [
      'shell',
      'rm -rf',
      file_utils.convert_to_posix_path(_DEVICE_FILES, 'tracks', '*'),
  ]
  # Issue ADB pull command to copy the directory
  response = adb_utils.issue_generic_request(adb_args, env)
  if response.status != adb_pb2.AdbResponse.OK:
    raise RuntimeError(
        f'ADB command failed with status {response.status}:'
        f' {response.generic.output.decode()}.'
    )


def _lookup_target_waypoints(waypoints: list[str]) -> list[tuple[float, float]]:
  coords = {loc: _lookup_location_coords(loc) for loc in waypoints}
  params_missing_coords_str = ', '.join(
      [f'"{c[0]}"' for c in coords.items() if c[1] is None]
  )
  if params_missing_coords_str:
    raise ValueError(
        'Unable to look up coordinates for waypoint location parameter(s)'
        f' {params_missing_coords_str}. Only lat/lon coordinate strings or'
        ' exact names from _PRELOADED_MAP_LOCATIONS supported.'
    )
  return [c[1] for c in coords.items() if c[1] is not None]


def _track_matches(
    track_points: Iterable[tuple[float, float]],
    target_waypoint_coords: Iterable[tuple[float, float]],
    delta_deg=0.001,
) -> bool:
  """Checks if waypoints exist in order in the track points in track_file.

  Args:
    track_points: Sequence of track coordinate points to match.
    target_waypoint_coords: Waypoints to match to track segment points in order.
    delta_deg:

  Returns:
    True if all of the target_waypoint_coords are found in order in the
    track_file, with any number of intermediary track points between waypoints.
  """
  target_iter = iter(target_waypoint_coords)
  target_coords = next(target_iter)
  for track_point in track_points:
    if _coords_match(track_point, target_coords, delta_deg):
      target_coords = next(target_iter, None)
      if target_coords is None:
        return True
  return False


def _track_points(
    tracks_root: ElementTree.Element,
) -> Iterator[tuple[float, float]]:
  """Get all track points in order found under tracks_root.

  Args:
    tracks_root: XML element that contains trk -> trkseg -> trkpt elements.

  Yields:
    track points in order.
  """
  for track in tracks_root.findall('gpx:trk', _FAVORITES_XML_NAMESPACES):
    for segment in track.findall('gpx:trkseg', _FAVORITES_XML_NAMESPACES):
      for point in segment.findall('gpx:trkpt', _FAVORITES_XML_NAMESPACES):
        yield (float(point.attrib.get('lat')), float(point.attrib.get('lon')))





# ============================================================================
# 封装验证函数：检查 OsmAnd 地图操作是否成功
# ============================================================================

# 数据库路径
_MARKERS_DB_PATH = '/data/data/net.osmand/databases/map_markers_db'
_MARKERS_TABLE_NAME = 'map_markers'


def get_markers(env: interface.AsyncEnv) -> list[sqlite_schema_utils.OsmAndMapMarker]:
    """获取所有地图标记。

    Args:
        env: Android 环境接口。

    Returns:
        OsmAndMapMarker 对象列表。
    """
    rows = sqlite_utils.get_rows_from_remote_device(
        _MARKERS_TABLE_NAME,
        _MARKERS_DB_PATH,
        sqlite_schema_utils.OsmAndMapMarker,
        env,
    )
    print(f"[DEBUG] Found {len(rows)} markers")
    return rows


def clear_markers(env: interface.AsyncEnv) -> None:
    """清空所有地图标记。

    Args:
        env: Android 环境接口。
    """
    sqlite_utils.delete_all_rows_from_table(_MARKERS_TABLE_NAME, _MARKERS_DB_PATH, env, 'osmand')
    print("[DEBUG] All markers cleared")


def add_marker(
    env: interface.AsyncEnv,
    lat: float,
    lon: float,
    description: str = "",
    group_name: str = "",
) -> None:
    """添加一个地图标记。

    Args:
        env: Android 环境接口。
        lat: 纬度。
        lon: 经度。
        description: 标记描述。
        group_name: 分组名称。
    """
    import time
    marker = sqlite_schema_utils.OsmAndMapMarker(
        marker_id=str(int(time.time() * 1000)),
        marker_lat=lat,
        marker_lon=lon,
        marker_description=description,
        marker_active=1,
        marker_added=int(time.time()),
        marker_visited=0,
        group_name=group_name,
    )
    sqlite_utils.add_row(marker, _MARKERS_TABLE_NAME, _MARKERS_DB_PATH, env)
    print(f"[DEBUG] Added marker at ({lat}, {lon})")


def clear_favorites(env: interface.AsyncEnv) -> None:
    """清空所有收藏位置。

    Args:
        env: Android 环境接口。
    """
    _clear_favorites(env.controller)
    print("[DEBUG] All favorites cleared")


def get_favorites(env: interface.AsyncEnv) -> list[dict]:
    """获取所有收藏位置。

    Args:
        env: Android 环境接口。

    Returns:
        收藏位置列表，每个元素包含 name, lat, lon 字段。
    """
    favorites = []
    if not file_utils.check_file_exists(_FAVORITES_PATH, env.controller):
        print("[DEBUG] Favorites file not found")
        return favorites

    with file_utils.tmp_file_from_device(_FAVORITES_PATH, env.controller) as favorites_file:
        tree = ElementTree.parse(favorites_file)
        root = tree.getroot()
        for waypoint in root.findall('gpx:wpt', _FAVORITES_XML_NAMESPACES):
            name_elem = waypoint.find('gpx:name', _FAVORITES_XML_NAMESPACES)
            name = name_elem.text if name_elem is not None else ""
            lat = float(waypoint.attrib.get('lat', 0))
            lon = float(waypoint.attrib.get('lon', 0))
            favorites.append({'name': name, 'lat': lat, 'lon': lon})

    print(f"[DEBUG] Found {len(favorites)} favorites")
    return favorites


def validate_marker_added(
    env: interface.AsyncEnv,
    before_markers: list[sqlite_schema_utils.OsmAndMapMarker],
    expected_location: str,
    check_integrity: bool = True,
) -> bool:
    """验证地图标记是否被正确添加。

    Args:
        env: Android 环境接口。
        before_markers: 任务执行前的标记列表。
        expected_location: 期望的位置（地名或坐标字符串）。
        check_integrity: 是否检查其他标记完整性。

    Returns:
        True 如果验证通过，False 否则。
    """
    after_markers = get_markers(env)

    print(f"[DEBUG] Before markers: {len(before_markers)}")
    print(f"[DEBUG] After markers: {len(after_markers)}")
    print(f"[DEBUG] Expected location: '{expected_location}'")

    # 获取目标坐标
    expected_coords = _lookup_location_coords(expected_location)
    if expected_coords:
        print(f"[DEBUG] Target coordinates: lat={expected_coords[0]}, lon={expected_coords[1]}")
    else:
        print(f"[DEBUG] Could not resolve target coordinates for: {expected_location}")

    # 打印所有标记的坐标
    for i, marker in enumerate(after_markers):
        print(f"[DEBUG] Marker {i}: lat={marker.marker_lat}, lon={marker.marker_lon}")

    # 查找匹配的标记
    for marker in after_markers:
        if _marker_matches_location(marker, expected_location):
            # 检查是否是新添加的
            if marker not in before_markers:
                if check_integrity:
                    # 验证其他标记未被删除
                    for old_marker in before_markers:
                        if old_marker not in after_markers:
                            return False
                    if len(after_markers) != len(before_markers) + 1:
                        return False
                print(f"[DEBUG] Marker addition validated: True")
                return True

    print(f"[DEBUG] Marker addition validated: False")
    return False


def validate_markers_added(
    env: interface.AsyncEnv,
    before_markers: list[sqlite_schema_utils.OsmAndMapMarker],
    expected_locations: list[str],
    check_integrity: bool = True,
) -> bool:
    """验证多个地图标记是否被正确添加。

    Args:
        env: Android 环境接口。
        before_markers: 任务执行前的标记列表。
        expected_locations: 期望的位置列表（地名或坐标字符串）。
        check_integrity: 是否检查其他标记完整性。

    Returns:
        True 如果验证通过，False 否则。
    """
    after_markers = get_markers(env)

    print(f"[DEBUG] Before markers: {len(before_markers)}")
    print(f"[DEBUG] After markers: {len(after_markers)}")

    # 验证每个位置
    for location in expected_locations:
        print(f"[DEBUG] Expected location: '{location}'")
        found = False
        for marker in after_markers:
            if _marker_matches_location(marker, location):
                if marker not in before_markers:
                    found = True
                    break
        if not found:
            print(f"[DEBUG] Failed to validate marker: {location}")
            return False

    # 检查数量是否正确
    if check_integrity:
        expected_count = len(expected_locations)
        actual_count = len(after_markers) - len(before_markers)
        if actual_count != expected_count:
            print(f"[DEBUG] Count mismatch: expected {expected_count} new markers, got {actual_count}")
            return False

    print(f"[DEBUG] Multiple markers addition validated: True")
    return True


def validate_marker_deleted(
    env: interface.AsyncEnv,
    before_markers: list[sqlite_schema_utils.OsmAndMapMarker],
    location: str,
    check_integrity: bool = True,
) -> bool:
    """验证地图标记是否被正确删除。

    Args:
        env: Android 环境接口。
        before_markers: 任务执行前的标记列表。
        location: 要删除的位置（地名或坐标字符串）。
        check_integrity: 是否检查其他标记完整性。

    Returns:
        True 如果验证通过，False 否则。
    """
    after_markers = get_markers(env)

    print(f"[DEBUG] Before markers: {len(before_markers)}")
    print(f"[DEBUG] After markers: {len(after_markers)}")
    print(f"[DEBUG] Looking for marker to delete: location='{location}'")

    # 查找要删除的标记
    marker_to_delete = None
    for marker in before_markers:
        if _marker_matches_location(marker, location):
            marker_to_delete = marker
            break

    if marker_to_delete is None:
        print(f"[DEBUG] No marker found at location: {location}")
        return False

    print(f"[DEBUG] Marker to delete: lat={marker_to_delete.marker_lat}, lon={marker_to_delete.marker_lon}")

    # 检查标记是否已不在列表中
    if marker_to_delete in after_markers:
        print(f"[DEBUG] Marker still exists in after_markers")
        return False

    if check_integrity:
        # 验证其他标记未被删除
        for old_marker in before_markers:
            if old_marker != marker_to_delete and old_marker not in after_markers:
                return False
        if len(after_markers) != len(before_markers) - 1:
            return False

    print(f"[DEBUG] Marker deletion validated: True")
    return True


def validate_favorite_added(
    env: interface.AsyncEnv,
    before_favorites: list[dict],
    expected_location: str,
) -> bool:
    """验证收藏位置是否被正确添加。

    Args:
        env: Android 环境接口。
        before_favorites: 任务执行前的收藏列表。
        expected_location: 期望的位置（地名或坐标字符串）。

    Returns:
        True 如果验证通过，False 否则。
    """
    after_favorites = get_favorites(env)

    print(f"[DEBUG] Before favorites: {len(before_favorites)}")
    print(f"[DEBUG] After favorites: {len(after_favorites)}")
    print(f"[DEBUG] Expected location: '{expected_location}'")

    # 查找匹配的收藏
    for favorite in after_favorites:
        # 检查名称匹配
        if expected_location in favorite['name']:
            if favorite not in before_favorites:
                print(f"[DEBUG] Favorite addition validated: True")
                return True

        # 检查坐标匹配
        expected_coords = _lookup_location_coords(expected_location)
        if expected_coords:
            if _coords_match((favorite['lat'], favorite['lon']), expected_coords, 0.001):
                if favorite not in before_favorites:
                    print(f"[DEBUG] Favorite addition validated: True")
                    return True

    print(f"[DEBUG] Favorite addition validated: False")
    return False


def validate_favorite_deleted(
    env: interface.AsyncEnv,
    before_favorites: list[dict],
    location: str,
) -> bool:
    """验证收藏位置是否被正确删除。

    Args:
        env: Android 环境接口。
        before_favorites: 任务执行前的收藏列表。
        location: 要删除的位置（地名或坐标字符串）。

    Returns:
        True 如果验证通过，False 否则。
    """
    after_favorites = get_favorites(env)

    print(f"[DEBUG] Before favorites: {len(before_favorites)}")
    print(f"[DEBUG] After favorites: {len(after_favorites)}")
    print(f"[DEBUG] Looking for favorite to delete: location='{location}'")

    # 查找要删除的收藏
    favorite_to_delete = None
    for favorite in before_favorites:
        # 检查名称匹配
        if location in favorite['name']:
            favorite_to_delete = favorite
            break
        # 检查坐标匹配
        expected_coords = _lookup_location_coords(location)
        if expected_coords:
            if _coords_match((favorite['lat'], favorite['lon']), expected_coords, 0.001):
                favorite_to_delete = favorite
                break

    if favorite_to_delete is None:
        print(f"[DEBUG] No favorite found at location: {location}")
        return False

    # 检查收藏是否已不在列表中
    if favorite_to_delete in after_favorites:
        print(f"[DEBUG] Favorite still exists in after_favorites")
        return False

    print(f"[DEBUG] Favorite deletion validated: True")
    return True


def clear_tracks(env: interface.AsyncEnv) -> None:
    """清空所有保存的轨迹。

    Args:
        env: Android 环境接口。
    """
    _clear_tracks(env.controller)
    print("[DEBUG] All tracks cleared")


def validate_track_saved(
    env: interface.AsyncEnv,
    expected_waypoints: list[str],
) -> bool:
    """验证轨迹是否正确保存并包含指定路径点。

    Args:
        env: Android 环境接口。
        expected_waypoints: 期望的路径点列表（地名或坐标字符串）。

    Returns:
        True 如果验证通过，False 否则。
    """
    import os

    # 获取目标路径点坐标
    target_waypoint_coords = _lookup_target_waypoints(expected_waypoints)
    print(f"[DEBUG] Expected waypoints: {expected_waypoints}")
    print(f"[DEBUG] Target coordinates: {target_waypoint_coords}")

    tracks_dir = file_utils.convert_to_posix_path(_DEVICE_FILES, 'tracks')

    with file_utils.tmp_directory_from_device(tracks_dir, env.controller) as tracks_directory:
        track_files = os.listdir(tracks_directory)
        print(f"[DEBUG] Found {len(track_files)} track files")

        for track_file in track_files:
            print(f"[DEBUG] Checking track file: {track_file}")
            track_path = file_utils.convert_to_posix_path(tracks_directory, track_file)
            track_root = ElementTree.parse(track_path).getroot()

            # 获取轨迹点
            track_points = list(_track_points(track_root))
            print(f"[DEBUG] Track has {len(track_points)} points")

            # 打印前几个和后几个轨迹点
            if track_points:
                print(f"[DEBUG] First track point: lat={track_points[0][0]}, lon={track_points[0][1]}")
                print(f"[DEBUG] Last track point: lat={track_points[-1][0]}, lon={track_points[-1][1]}")

            # 检查是否包含所有目标路径点
            if _track_matches(track_points, target_waypoint_coords):
                print(f"[DEBUG] Track validation: True")
                return True

    print(f"[DEBUG] Track validation: False")
    return False
