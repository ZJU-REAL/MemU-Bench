#!/usr/bin/env python3
"""
Cross-platform: Restore ALL App Data to Emulator
Works on both Mac and Windows
Usage: python restore_app_data.py [data_directory]
"""

import os
import sys
import subprocess
import time
import re


def adb(*args):
    """Run adb command, return CompletedProcess with decoded output."""
    result = subprocess.run(["adb"] + list(args), capture_output=True)
    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")
    return subprocess.CompletedProcess(
        args=result.args, returncode=result.returncode,
        stdout=stdout, stderr=stderr,
    )


def adb_shell(cmd):
    """Run adb shell command."""
    return adb("shell", cmd)


def adb_push(local, remote):
    """Push a file/directory to device, return success."""
    result = adb("push", local, remote)
    if result.returncode != 0:
        print(f"    ERROR: Failed to push {os.path.basename(local)}")
        if result.stderr:
            for line in result.stderr.strip().splitlines():
                if "error" in line.lower():
                    print(f"           {line.strip()}")
        return False
    return True


def clean_remote_dir(remote_path):
    """Remove and recreate a remote directory for clean state."""
    adb_shell(f"rm -rf {remote_path}")
    adb_shell(f"mkdir -p {remote_path}")


def main():
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "./app_data_backup"

    print("========== Restore Emulator Data ==========")
    print(f"Data directory: {output_dir}")
    print()

    # Check directory exists
    if not os.path.isdir(output_dir):
        print(f"Error: Directory {output_dir} does not exist")
        sys.exit(1)

    # [1] Get root
    print("[1/7] Getting root access...")
    result = adb("root")
    print(f"Root status: {result.stdout.strip()}")

    # Wait for adb daemon to restart and device to come back online
    print("Waiting for device to reconnect...")
    time.sleep(3)
    adb("wait-for-device")
    time.sleep(1)

    uid_result = adb_shell("id")
    if "uid=0" not in uid_result.stdout:
        print(f"Warning: Root access not available. Current: {uid_result.stdout.strip()}")
    else:
        print("Root access confirmed.")
    print()

    # [2] Stop all user apps
    print("[2/7] Stopping all user apps...")
    result = adb_shell("pm list packages -3")
    for line in result.stdout.strip().splitlines():
        pkg = line.strip().split(":", 1)[-1]
        if pkg:
            adb_shell(f"am force-stop {pkg}")
    print("All apps stopped")
    print()

    # [3] Restore app data
    print("[3/7] Restoring app data...")
    success = 0
    skipped = 0

    for entry in sorted(os.listdir(output_dir)):
        pkg_dir = os.path.join(output_dir, entry)
        if not os.path.isdir(pkg_dir):
            continue
        if entry.startswith("media_") or entry.startswith("root_"):
            continue

        pkg = entry
        print(f"  Restoring {pkg} ...")

        # Check if app is installed
        check = adb_shell(f"pm list packages | grep ':{pkg}$'")
        if not check.stdout.strip():
            check2 = adb_shell(f"[ -d /data/data/{pkg} ]")
            if check2.returncode != 0:
                print(f"    Warning: App {pkg} not found, skip")
                skipped += 1
                continue

        # Stop app
        adb_shell(f"am force-stop {pkg}")

        # Get app UID
        uid = None
        dumpsys = adb_shell(f"dumpsys package {pkg}")
        for line in dumpsys.stdout.splitlines():
            if "userId=" in line:
                m = re.search(r"userId=(\d+)", line)
                if m:
                    uid = m.group(1)
                break

        # Restore internal data
        data_dir = os.path.join(pkg_dir, "data")
        if os.path.isdir(data_dir):
            print("    Restore internal data...")
            adb_shell(f"rm -rf /data/data/{pkg}/*")

            for item in os.listdir(data_dir):
                item_path = os.path.join(data_dir, item)
                if os.path.isdir(item_path):
                    print(f"      - {item}/")
                    adb_push(item_path, f"/data/data/{pkg}/{item}/")
                elif os.path.isfile(item_path):
                    print(f"      - {item}")
                    adb_push(item_path, f"/data/data/{pkg}/{item}")

            if uid:
                adb_shell(f"chown -R {uid}:{uid} /data/data/{pkg}")
                adb_shell(f"chmod -R 755 /data/data/{pkg}")
            success += 1

        # Restore external data
        ext_dir = os.path.join(pkg_dir, "external")
        if os.path.isdir(ext_dir):
            print("    Restore external data...")
            adb_shell(f"rm -rf /sdcard/Android/data/{pkg}/*")

            for item in os.listdir(ext_dir):
                item_path = os.path.join(ext_dir, item)
                if os.path.isdir(item_path):
                    print(f"      - {item}/")
                    adb_push(item_path, f"/sdcard/Android/data/{pkg}/{item}/")
                elif os.path.isfile(item_path):
                    print(f"      - {item}")
                    adb_push(item_path, f"/sdcard/Android/data/{pkg}/{item}")

            if uid:
                adb_shell(f"chown -R {uid}:{uid} /sdcard/Android/data/{pkg}")
                adb_shell(f"chmod -R 755 /sdcard/Android/data/{pkg}")
            success += 1

        # Restore user_de data (/data/user_de/0/) - e.g., alarm data
        user_de_dir = os.path.join(pkg_dir, "user_de")
        if os.path.isdir(user_de_dir):
            print("    Restore user_de data...")
            adb_shell(f"rm -rf /data/user_de/0/{pkg}/*")

            for item in os.listdir(user_de_dir):
                item_path = os.path.join(user_de_dir, item)
                if os.path.isdir(item_path):
                    print(f"      - {item}/")
                    adb_push(item_path, f"/data/user_de/0/{pkg}/{item}/")
                elif os.path.isfile(item_path):
                    print(f"      - {item}")
                    adb_push(item_path, f"/data/user_de/0/{pkg}/{item}")

            if uid:
                adb_shell(f"chown -R {uid}:{uid} /data/user_de/0/{pkg}")
                adb_shell(f"chmod -R 755 /data/user_de/0/{pkg}")
            success += 1

    print(f"  Success: {success}, Skipped: {skipped}")
    print()

    # [4] Restore media directories
    print("[4/7] Restoring shared media...")
    for entry in sorted(os.listdir(output_dir)):
        if not entry.startswith("media_"):
            continue
        media_dir = os.path.join(output_dir, entry)
        if not os.path.isdir(media_dir):
            continue

        target_name = entry[len("media_"):]
        remote_dir = f"/sdcard/{target_name}"
        print(f"  Restore {entry} -> {remote_dir}/ ...")

        # Clean: remove entire dir then recreate (avoids leftover dirs from previous failed pushes)
        clean_remote_dir(remote_dir)

        # Check for nested structure (e.g., media_DCIM/DCIM/)
        nested_dir = os.path.join(media_dir, target_name)
        src_dir = nested_dir if os.path.isdir(nested_dir) else media_dir

        if os.path.isdir(nested_dir):
            print("    (nested structure detected)")

        for item in os.listdir(src_dir):
            item_path = os.path.join(src_dir, item)
            if os.path.isdir(item_path):
                print(f"    - {item}/")
                adb_push(item_path, f"{remote_dir}/{item}/")
            elif os.path.isfile(item_path):
                print(f"    - {item}")
                adb_push(item_path, f"{remote_dir}/{item}")

    print()

    # [5] Restore root directories
    print("[5/7] Restoring root directories...")
    for entry in sorted(os.listdir(output_dir)):
        if not entry.startswith("root_"):
            continue
        root_dir = os.path.join(output_dir, entry)
        if not os.path.isdir(root_dir):
            continue

        root_name = entry[len("root_"):]

        # Special handling: root_obb -> /sdcard/Android/obb
        if root_name == "obb":
            target_path = "/sdcard/Android/obb"
        else:
            target_path = f"/sdcard/{root_name}"

        print(f"  Restore {root_name} -> {target_path}/ ...")

        # Clean: remove entire dir then recreate
        clean_remote_dir(target_path)

        # Check for nested structure (e.g., root_Music/Music/)
        nested_dir = os.path.join(root_dir, root_name)
        src_dir = nested_dir if os.path.isdir(nested_dir) else root_dir

        if os.path.isdir(nested_dir):
            print("    (nested structure detected)")

        for item in os.listdir(src_dir):
            item_path = os.path.join(src_dir, item)
            if os.path.isdir(item_path):
                print(f"    - {item}/")
                adb_push(item_path, f"{target_path}/{item}/")
            elif os.path.isfile(item_path):
                print(f"    - {item}")
                adb_push(item_path, f"{target_path}/{item}")

    print()

    # [6] Trigger media scan
    print("[6/7] Triggering media scan...")
    media_dirs = ["Music", "Movies", "Pictures", "DCIM", "Download"]
    for d in media_dirs:
        adb_shell(f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/{d}")
    print("Done")
    print()

    # [7] Fix permissions
    print("[7/7] Fixing permissions...")
    adb_shell("chmod -R 755 /sdcard/Android/data/")
    adb_shell("chmod -R 755 /data/data/")
    print("Done")
    print()

    # [8] Restore emulator time and timezone
    print("[8/8] Restoring emulator time and timezone...")
    time_file = os.path.join(output_dir, "emulator_time.txt")
    if os.path.isfile(time_file):
        with open(time_file, "r") as f:
            lines = f.read().strip().splitlines()
        if len(lines) >= 1:
            timestamp = lines[0].strip()
            print(f"  Saved timestamp: {timestamp}")
            # Convert timestamp to date command format: MMDDHHmmYY.SS
            from datetime import datetime, timezone
            dt = datetime.fromtimestamp(int(timestamp), timezone.utc)
            # Format: MM DD HH mm YY . SS
            date_cmd = f"{dt.month:02d}{dt.day:02d}{dt.hour:02d}{dt.minute:02d}{dt.year % 100:02d}.{dt.second:02d}"
            print(f"  Date command: {date_cmd}")
            # Execute restore commands
            print("  Setting auto_time=0...")
            adb_shell("settings put global auto_time 0")
            print("  Setting auto_time_zone=0...")
            adb_shell("settings put global auto_time_zone 0")
            print("  Setting time_12_24=24...")
            adb_shell("settings put system time_12_24 24")
            print("  Setting timezone via alarm service...")
            adb_shell("service call alarm 3 s16 UTC")
            print("  Getting root...")
            adb("root")
            time.sleep(2)
            adb("wait-for-device")
            time.sleep(1)
            print(f"  Setting date {date_cmd}...")
            adb_shell(f"date {date_cmd}")
            # Verify
            verify_result = adb_shell("date")
            print(f"  Restored: {verify_result.stdout.strip()}")
            print(f"  Time restored successfully")
        else:
            print("  Warning: Invalid time file format")
    else:
        print("  No saved time found, skipping")
    print()

    print("========== Restore Complete ==========")
    print(f"App data restored: {success}")
    print(f"Apps skipped: {skipped}")


if __name__ == "__main__":
    main()