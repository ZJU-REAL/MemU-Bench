#!/usr/bin/env python3
"""
Cross-platform: Backup ALL App Data from Emulator
Works on both Mac and Windows
Usage: python backup_app_data.py [output_directory]
"""

import os
import sys
import subprocess
import time
import datetime
import shutil
import tempfile

# Temp directory on device for pulling internal data
BACKUP_TMP = "/sdcard/.backup_tmp"


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


def device_path_exists(path):
    """Check if a path exists on the device."""
    result = adb_shell(f'[ -e "{path}" ]')
    return result.returncode == 0


def device_dir_has_files(path):
    """Check if a directory on device has any real files (excluding .thumbnails)."""
    result = adb_shell(f'find "{path}" -type f ! -path "*/.thumbnails/*" 2>/dev/null | wc -l')
    try:
        return int(result.stdout.strip()) > 0
    except ValueError:
        return False


def adb_pull(remote, local_path):
    """
    Pull file/directory from device to local_path.
    Uses a local ASCII temp dir in current directory to avoid Windows non-ASCII path issues,
    then moves the result to the final destination using Python.
    """
    # Use current directory for temp to avoid Windows user path issues (e.g., Chinese username)
    temp_base = os.path.join(os.getcwd(), ".adb_temp")
    os.makedirs(temp_base, exist_ok=True)
    local_tmp = tempfile.mkdtemp(dir=temp_base, prefix="adb_pull_")
    result = adb("pull", remote, local_tmp)

    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip()
        for line in err.splitlines():
            line = line.strip()
            if line and "bytes in" not in line:
                print(f"    pull error: {line}")
        shutil.rmtree(local_tmp, ignore_errors=True)
        return False

    # adb pull creates local_tmp/<basename_of_remote>/...
    remote_name = remote.rstrip("/").split("/")[-1]
    pulled = os.path.join(local_tmp, remote_name)

    if os.path.isdir(pulled):
        if os.path.exists(local_path):
            shutil.rmtree(local_path)
        shutil.move(pulled, local_path)
    elif os.path.exists(local_tmp):
        if os.path.exists(local_path):
            shutil.rmtree(local_path)
        shutil.move(local_tmp, local_path)
        local_tmp = local_path

    shutil.rmtree(local_tmp, ignore_errors=True)
    return True


def adb_pull_internal(remote_path, local_path):
    """
    Pull from /data/data/ via temp copy on /sdcard/.
    adb pull cannot directly access /data/data/ on some platforms (Windows),
    so we copy to /sdcard/ first using root shell, then pull from there.
    """
    pkg_name = remote_path.split("/")[-1]
    tmp_remote = f"{BACKUP_TMP}/{pkg_name}"

    # Copy to /sdcard/ temp (root shell can access /data/data/)
    adb_shell(f"mkdir -p {BACKUP_TMP}")
    adb_shell(f"rm -rf {tmp_remote}")
    adb_shell(f"cp -r {remote_path} {tmp_remote}")
    adb_shell(f"chmod -R 755 {tmp_remote}")

    # Pull from /sdcard/ temp
    ok = adb_pull(tmp_remote, local_path)

    # Clean up device temp
    adb_shell(f"rm -rf {tmp_remote}")

    return ok


def main():
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "./app_data_backup"

    print("========== Start Emulator Data Backup ==========")
    print(f"Output directory: {output_dir}")
    print(f"Time: {datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
    print()

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # [1] Get root
    print("[1/6] Getting root access...")
    result = adb("root")
    print(f"Root status: {result.stdout.strip()}")

    # Wait for adb daemon to restart and device to come back online
    print("Waiting for device to reconnect...")
    time.sleep(3)
    adb("wait-for-device")
    time.sleep(1)

    uid_result = adb_shell("id")
    if "uid=0" not in uid_result.stdout:
        print(f"WARNING: Root access not available. Current: {uid_result.stdout.strip()}")
        print("Internal data (/data/data/) cannot be backed up without root.")
        has_root = False
    else:
        print("Root access confirmed.")
        has_root = True
    print()

    # [2] Get all app packages
    print("[2/6] Getting all app list...")
    result = adb_shell("pm list packages")
    packages = []
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if ":" in line:
            pkg = line.split(":", 1)[1]
            packages.append(pkg)
    print(f"Found {len(packages)} apps (including system apps)")
    print()

    # [3] Export each app's data
    print("[3/6] Exporting app data...")
    success_count = 0
    failed_count = 0
    skip_count = 0

    for pkg in packages:
        pkg_dir = os.path.join(output_dir, pkg)
        os.makedirs(pkg_dir, exist_ok=True)
        has_data = False

        # Export internal data (/data/data/) - requires root
        if has_root and device_path_exists(f"/data/data/{pkg}"):
            print(f"  Export {pkg} (internal)...")
            if adb_pull_internal(f"/data/data/{pkg}", os.path.join(pkg_dir, "data")):
                success_count += 1
                has_data = True
            else:
                failed_count += 1

        # Export user_de data (/data/user_de/0/) - requires root (e.g., alarm data)
        if has_root and device_path_exists(f"/data/user_de/0/{pkg}"):
            print(f"  Export {pkg} (user_de)...")
            if adb_pull_internal(f"/data/user_de/0/{pkg}", os.path.join(pkg_dir, "user_de")):
                success_count += 1
                has_data = True
            else:
                failed_count += 1

        # Export external data (/sdcard/Android/data/)
        if device_path_exists(f"/sdcard/Android/data/{pkg}"):
            print(f"  Export {pkg} (external)...")
            if adb_pull(f"/sdcard/Android/data/{pkg}", os.path.join(pkg_dir, "external")):
                success_count += 1
                has_data = True
            else:
                failed_count += 1

        if not has_data:
            skip_count += 1

    # Clean up device temp directory
    adb_shell(f"rm -rf {BACKUP_TMP}")

    print()

    # [4] Export emulator time and timezone
    print("[4/6] Exporting emulator time and timezone...")
    # Get timestamp (seconds since epoch)
    timestamp_result = adb_shell("date +%s")
    timestamp = timestamp_result.stdout.strip()
    # Get timezone
    timezone_result = adb_shell("getprop persist.sys.timezone")
    timezone = timezone_result.stdout.strip()
    # Get human readable time
    time_result = adb_shell("date +'%Y-%m-%d %H:%M:%S'")
    emulator_time = time_result.stdout.strip()
    print(f"  Emulator time: {emulator_time}")
    print(f"  Timestamp: {timestamp}")
    print(f"  Timezone: {timezone}")
    time_file = os.path.join(output_dir, "emulator_time.txt")
    with open(time_file, "w") as f:
        f.write(f"{timestamp}\n")
        f.write(f"{timezone}\n")
        f.write(f"{emulator_time}\n")
    print()

    # [5] Export shared media directories
    print("[5/6] Exporting shared media...")
    media_dirs = ["DCIM", "Pictures", "Download", "Documents", "WhatsApp", "Telegram"]

    for media_name in media_dirs:
        standard_path = f"/sdcard/{media_name}"
        alt_path = f"/sdcard/media_{media_name}"
        backup_dir = os.path.join(output_dir, f"media_{media_name}")

        if device_path_exists(standard_path):
            if device_dir_has_files(standard_path):
                print(f"  Export {media_name} (from standard path)...")
                os.makedirs(backup_dir, exist_ok=True)
                adb_pull(standard_path, backup_dir)
            else:
                # Standard path is empty, try media_* path
                if device_path_exists(alt_path) and device_dir_has_files(alt_path):
                    print(f"  Export {media_name} (from media_{media_name})...")
                    adb_shell(f"cp -r {alt_path}/* {standard_path}/")
                    os.makedirs(backup_dir, exist_ok=True)
                    adb_pull(standard_path, backup_dir)

    print()

    # [6] Export root-level data directories
    print("[6/6] Exporting root directories...")
    root_dirs = [
        ("/sdcard/Android/obb", "root_obb"),
        ("/sdcard/Download", "root_Download"),
        ("/sdcard/Pictures", "root_Pictures"),
        ("/sdcard/Movies", "root_Movies"),
        ("/sdcard/Music", "root_Music"),
        ("/sdcard/Documents", "root_Documents"),
    ]

    for remote_path, dir_name in root_dirs:
        # Skip if already exported as media_
        media_name = dir_name[len("root_"):]
        media_backup = os.path.join(output_dir, f"media_{media_name}")
        if os.path.isdir(media_backup):
            continue

        if device_path_exists(remote_path):
            backup_dir = os.path.join(output_dir, dir_name)
            print(f"  Export {remote_path}...")
            adb_pull(remote_path, backup_dir)

    print()

    # [7] Generate manifest
    print("[7/7] Generating manifest...")
    manifest_path = os.path.join(output_dir, "manifest.txt")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("Backup Manifest\n")
        f.write("===============\n")
        f.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Root access: {'Yes' if has_root else 'No'}\n")
        f.write(f"Total Packages: {len(packages)}\n")
        f.write(f"Successful: {success_count}\n")
        f.write(f"Failed: {failed_count}\n")
        f.write(f"Skipped (no data): {skip_count}\n")
        f.write("\nPackage List:\n")
        for pkg in packages:
            f.write(f"  {pkg}\n")

    print()
    # Clean up local temp directory
    temp_base = os.path.join(os.getcwd(), ".adb_temp")
    if os.path.exists(temp_base):
        shutil.rmtree(temp_base, ignore_errors=True)
        print("Cleaned up temp directory")

    print()
    print("========== Backup Complete ==========")
    print(f"Root access: {'Yes' if has_root else 'No'}")
    print(f"Success: {success_count}")
    print(f"Failed: {failed_count}")
    print(f"Skipped (no data): {skip_count}")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()