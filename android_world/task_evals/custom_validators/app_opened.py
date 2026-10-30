

"""Validator for checking whether a specific app is in the foreground."""

import re
from android_world.env import adb_utils
from android_world.env import interface


# Mapping from app name patterns to package names
_APP_PATTERN_TO_PACKAGE = {
    'google chrome': 'com.android.chrome',
    'settings': 'com.android.settings',
    'youtube': 'com.google.android.youtube',
    'gmail': 'com.google.android.gm',
    'google maps': 'com.google.android.apps.maps',
    'google photos': 'com.google.android.apps.photos',
    'google calendar': 'com.google.android.calendar',
    'camera': 'com.android.camera2',
    'audio recorder': 'com.dimowner.audiorecorder',
    'google drive': 'com.google.android.apps.docs',
    'clock': 'com.google.android.deskclock',
    'google search': 'com.google.android.googlequicksearchbox',
    'contacts': 'com.google.android.contacts',
    'android world': 'com.example.androidworld',
    'files': 'com.google.android.documentsui',
    'markor': 'net.gsantner.markor',
    'clipper': 'ca.zgrs.clipper',
    'messages': 'com.google.android.apps.messaging',
    'simple sms messenger': 'com.simplemobiletools.smsmessenger',
    'phone': 'com.google.android.dialer',
    'simple calendar': 'com.simplemobiletools.calendar.pro',
    'simple gallery': 'com.simplemobiletools.gallery.pro',
    'simple gallery pro': 'com.simplemobiletools.gallery.pro',
    'miniwob': 'com.google.androidenv.miniwob',
    'simple draw': 'com.simplemobiletools.draw.pro',
    'pro expense': 'com.arduia.expense',
    'broccoli': 'com.flauschcode.broccoli',
    'osmand': 'net.osmand',
    'tasks': 'org.tasks',
    'open tracks': 'de.dennisguse.opentracks',
    'joplin': 'net.cozic.joplin',
    'retro music': 'code.name.monkey.retromusic',
    'calculator': 'com.marktka.calculatorYou',
    'chilemei': 'com.test.chilemei',
    'taodian': 'com.testmall.app',
    'tuantuanwaimai': 'com.test.tuantuan',
    'jingdian': 'com.test.jingdian',
    '2048': 'org.andstatus.game2048',
    'chess': 'com.vayunmathur.games.chess',
    'gauguin': 'org.piepmeyer.gauguin',
    'solitairecg': 'net.sourceforge.solitaire_cg',
    'yt music': 'com.google.android.apps.youtube.music',
    'weather': 'org.breezyweather',
    'lxreader': 'io.gitlab.coolreader_ng.lxreader.fdroid',
    'librera fd': 'com.foobnix.pro.pdf.reader',
}

# Reverse mapping: package -> app name
_PACKAGE_TO_APP = {v: k for k, v in _APP_PATTERN_TO_PACKAGE.items()}


def get_foreground_app(env: interface.AsyncEnv) -> str:
  """Get the current foreground app name.

  Uses dumpsys window to find the currently focused window and extracts
  the package name, then maps it to an app name.

  Args:
    env: The Android environment interface.

  Returns:
    App name string (e.g., 'solitairecg', 'settings'), or empty string
    if the foreground app cannot be determined.
  """
  response = adb_utils.issue_generic_request(
      ['shell', 'dumpsys', 'window'],
      env.controller,
  )

  output = response.generic.output.decode('utf-8', errors='ignore')

  # Parse mCurrentFocus
  # Format: mCurrentFocus=Window{hash u0 package/activity}
  match = re.search(r'mCurrentFocus=Window\{[^\}]*\s+(\S+)\s*\}', output)
  if match:
    activity_str = match.group(1)
    if activity_str and activity_str != 'null':
      # Remove taskId prefix if present
      if ':' in activity_str:
        activity_str = activity_str.split(':', 1)[1]
      # Extract package name (before '/' or the whole string)
      if '/' in activity_str:
        package = activity_str.split('/')[0]
      else:
        package = activity_str
      if package and package != 'null':
        return _PACKAGE_TO_APP.get(package, package)

  # Fallback: Try mFocusedApp
  # Format: mFocusedApp=ActivityRecord{hash u0 package/activity t123}
  focused_match = re.search(
      r'mFocusedApp=ActivityRecord\{[^\}]*\s+(\S+)\s+', output
  )
  if focused_match:
    activity_str = focused_match.group(1)
    if activity_str and activity_str != 'null':
      if ':' in activity_str:
        activity_str = activity_str.split(':', 1)[1]
      if '/' in activity_str:
        package = activity_str.split('/')[0]
      else:
        package = activity_str
      if package and package != 'null':
        return _PACKAGE_TO_APP.get(package, package)

  return ''


def validate_app_opened(
    env: interface.AsyncEnv,
    expected_app: str,
) -> bool:
  """Validate that a specific app is currently in the foreground.

  Args:
    env: The Android environment interface.
    expected_app: The expected app name (e.g., 'solitairecg').

  Returns:
    True if the expected app is in the foreground, False otherwise.
  """
  current_app = get_foreground_app(env)
  print(f"[DEBUG] Current foreground app: '{current_app}', expected: '{expected_app}'")
  return current_app.lower() == expected_app.lower()
