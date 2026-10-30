

"""Validations for Retro Music app.

This module provides functions to validate Retro Music operations
by checking the underlying SQLite database.
"""

import dataclasses
import os
import xml.etree.ElementTree as ET
from typing import Optional

from android_world.env import interface
from android_world.task_evals.utils import sqlite_schema_utils
from android_world.task_evals.utils import sqlite_utils
from android_world.utils import file_utils


_APP_NAME = 'retro music'
_PLAYLIST_DB_PATH = (
    '/data/data/code.name.monkey.retromusic/databases/playlist.db'
)
_PLAYBACK_DB_PATH = (
    '/data/data/code.name.monkey.retromusic/databases/music_playback_state.db'
)
_RECENT_PREFS_PATH = (
    '/data/data/code.name.monkey.retromusic/shared_prefs/retro_recent.xml'
)


def _get_playlist_info_query() -> str:
  """Gets query for fetching playlists and their associated files."""
  return """
    SELECT
        pe.playlist_name AS playlist_name,
        se.title AS media_file_name,
        se.duration AS duration_ms,
        ROW_NUMBER() OVER (
            PARTITION BY pe.playlist_name
            ORDER BY se.song_key
        ) - 1 AS order_in_playlist
    FROM
        PlaylistEntity pe
        JOIN SongEntity se ON pe.playlist_id = se.playlist_creator_id
    ORDER BY
        pe.playlist_name,
        order_in_playlist;
    """


def get_playlist_data(
    env: interface.AsyncEnv,
) -> list[sqlite_schema_utils.PlaylistInfo]:
  """Get playlist data from the database.

  Args:
    env: The Android environment interface.

  Returns:
    A list of PlaylistInfo objects.
  """
  with env.controller.pull_file(
      _PLAYLIST_DB_PATH, timeout_sec=3
  ) as local_db_directory:
    local_db_path = file_utils.convert_to_posix_path(
        local_db_directory, os.path.split(_PLAYLIST_DB_PATH)[1]
    )
    return sqlite_utils.execute_query(
        _get_playlist_info_query(),
        local_db_path,
        sqlite_schema_utils.PlaylistInfo,
    )


def get_playing_queue(env: interface.AsyncEnv) -> list[str]:
  """Get the current playing queue from the database.

  Args:
    env: The Android environment interface.

  Returns:
    A list of song titles in the playing queue.
  """

  @dataclasses.dataclass(frozen=True)
  class Queue(sqlite_schema_utils.SQLiteRow):
    title: str

  with env.controller.pull_file(
      _PLAYBACK_DB_PATH, timeout_sec=3
  ) as local_db_directory:
    local_db_path = file_utils.convert_to_posix_path(
        local_db_directory, os.path.split(_PLAYBACK_DB_PATH)[1]
    )
    result = sqlite_utils.execute_query(
        'SELECT title from playing_queue;',
        local_db_path,
        Queue,
    )
    return [r.title for r in result]


def get_current_playing_song(env: interface.AsyncEnv) -> Optional[str]:
  """Get the currently playing song title.

  This function reads the Retro Music shared preferences file
  (retro_recent.xml) which stores the currently playing song info.

  Args:
    env: The Android environment interface.

  Returns:
    The title of the currently playing song, or None if no song is playing.
  """
  try:
    with env.controller.pull_file(
        _RECENT_PREFS_PATH, timeout_sec=3
    ) as local_dir:
      local_path = file_utils.convert_to_posix_path(
          local_dir, os.path.split(_RECENT_PREFS_PATH)[1]
      )
      tree = ET.parse(local_path)
      root = tree.getroot()
      for string_elem in root.findall('string'):
        if string_elem.get('name') == 'song_title':
          return string_elem.text
    return None
  except Exception as e:
    print(f"[DEBUG] Error getting current playing song: {e}")
    return None


def validate_song_playing(
    env: interface.AsyncEnv,
    expected_song_title: str,
    fuzzy_match: bool = True,
) -> bool:
  """Validate that a specific song is currently playing.

  Args:
    env: The Android environment interface.
    expected_song_title: The expected song title.
    fuzzy_match: If True, use fuzzy matching (ignore case, strip whitespace).

  Returns:
    True if the expected song is currently playing, False otherwise.
  """
  current_song = get_current_playing_song(env)

  print(f"[DEBUG] Expected song: {expected_song_title}")
  print(f"[DEBUG] Current playing song: {current_song}")

  if current_song is None:
    print("[DEBUG] No song is currently playing")
    return False

  if fuzzy_match:
    expected_normalized = expected_song_title.lower().strip()
    current_normalized = current_song.lower().strip()
    is_match = expected_normalized == current_normalized
  else:
    is_match = expected_song_title == current_song

  print(f"[DEBUG] Song playing validation result: {is_match}")
  return is_match


def validate_playlist_created(
    env: interface.AsyncEnv,
    expected_playlist_name: str,
    expected_songs: list[str],
    fuzzy_match_title: bool = True,
) -> bool:
  """Validate that a playlist has been created with the expected songs.

  Args:
    env: The Android environment interface.
    expected_playlist_name: The expected playlist name.
    expected_songs: List of expected song titles in the playlist.
    fuzzy_match_title: If True, use fuzzy matching for playlist name.

  Returns:
    True if the playlist was created correctly, False otherwise.
  """
  playlists = get_playlist_data(env)

  print(f"[DEBUG] Expected playlist: {expected_playlist_name}")
  print(f"[DEBUG] Expected songs: {expected_songs}")
  print(f"[DEBUG] Found {len(playlists)} playlist entries")

  # Find the matching playlist
  matching_playlist = None
  for playlist in playlists:
    if fuzzy_match_title:
      if playlist.playlist_name.lower().strip() == expected_playlist_name.lower().strip():
        matching_playlist = playlist
        break
    else:
      if playlist.playlist_name == expected_playlist_name:
        matching_playlist = playlist
        break

  if not matching_playlist:
    print(f"[DEBUG] Playlist '{expected_playlist_name}' not found")
    return False

  # Get all songs in the playlist
  playlist_songs = [
      p.media_file_name for p in playlists
      if p.playlist_name == matching_playlist.playlist_name
  ]

  print(f"[DEBUG] Found songs in playlist: {playlist_songs}")

  # Check if all expected songs are present (order matters)
  if len(playlist_songs) != len(expected_songs):
    print(f"[DEBUG] Song count mismatch: expected {len(expected_songs)}, got {len(playlist_songs)}")
    return False

  for expected, actual in zip(expected_songs, playlist_songs):
    if fuzzy_match_title:
      if expected.lower().strip() != actual.lower().strip():
        print(f"[DEBUG] Song mismatch: expected '{expected}', got '{actual}'")
        return False
    else:
      if expected != actual:
        print(f"[DEBUG] Song mismatch: expected '{expected}', got '{actual}'")
        return False

  print("[DEBUG] Playlist validation passed")
  return True


def validate_playing_queue(
    env: interface.AsyncEnv,
    expected_songs: list[str],
    fuzzy_match: bool = True,
) -> bool:
  """Validate that the playing queue contains the expected songs in order.

  Args:
    env: The Android environment interface.
    expected_songs: List of expected song titles in the queue.
    fuzzy_match: If True, use fuzzy matching for song titles.

  Returns:
    True if the playing queue matches the expected songs, False otherwise.
  """
  queue = get_playing_queue(env)

  print(f"[DEBUG] Expected queue: {expected_songs}")
  print(f"[DEBUG] Actual queue: {queue}")

  if len(queue) != len(expected_songs):
    print(f"[DEBUG] Queue length mismatch: expected {len(expected_songs)}, got {len(queue)}")
    return False

  for expected, actual in zip(expected_songs, queue):
    if fuzzy_match:
      if expected.lower().strip() != actual.lower().strip():
        print(f"[DEBUG] Queue song mismatch: expected '{expected}', got '{actual}'")
        return False
    else:
      if expected != actual:
        print(f"[DEBUG] Queue song mismatch: expected '{expected}', got '{actual}'")
        return False

  print("[DEBUG] Playing queue validation passed")
  return True