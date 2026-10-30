#!/usr/bin/env python3
"""Batch restore app data from operated_app_data and create emulator snapshots.

This script iterates through user_* directories in operated_app_data,
restores each to the emulator, and saves emulator snapshots.

Usage:
    python batch_restore_and_snapshot.py
    python batch_restore_and_snapshot.py --install-apps
    python batch_restore_and_snapshot.py --install-apps --apk-dir ./apks

The script will:
1. Optionally install apps from APK directory (if --install-apps specified)
   - After installing apps, it will automatically setup apps (handle first-run popups)
2. Iterate through user_0/short, user_0/medium, user_0/long, ... directories in operated_app_data
3. For each directory:
   - Restore data to emulator using restore_app_data.sh/bat
   - Save emulator snapshot snapshot_0_short, snapshot_0_medium, snapshot_0_long, etc.
"""

import argparse
import os
import platform
import re
import subprocess
import sys
import glob
import logging

# Add android_world to path

from android_world.env import android_world_controller
from android_world.env import interface
from android_world.env.setup_device import setup

# Configuration
# Base directory where this script is located (project root)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OPERATED_APP_DATA_DIR = os.path.join(BASE_DIR, "user_database")

# Auto-detect OS and select appropriate restore script

RESTORE_SCRIPT = os.path.join(BASE_DIR, "move_data", "restore_app_data.py")


def get_data_dirs():
    """Get all data directories (user_*/short, user_*/medium, user_*/long) sorted by user number then category."""
    data_dirs = []
    pattern = os.path.join(OPERATED_APP_DATA_DIR, "user_*")
    user_dirs = sorted(glob.glob(pattern), key=lambda x: int(os.path.basename(x).split("_")[-1]))
    for user_dir in user_dirs:
        for category in ["short", "medium", "long"]:
            category_dir = os.path.join(user_dir, category)
            if os.path.isdir(category_dir):
                data_dirs.append(category_dir)
    return data_dirs


def restore_app_data(data_dir: str) -> bool:
    """Restore app data to emulator using restore_app_data.sh."""
    print(f"\n{'='*60}")
    print(f"Restoring data from: {data_dir}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            ['python', RESTORE_SCRIPT, data_dir],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        print(result.stdout)
        if result.stderr:
            print(f"STDERR: {result.stderr}")

        if result.returncode != 0:
            print(f"ERROR: Restore failed with return code {result.returncode}")
            return False

        print("Restore completed successfully")
        return True

    except subprocess.TimeoutExpired:
        print("ERROR: Restore timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"ERROR: Restore failed with exception: {e}")
        return False


def save_emulator_snapshot(snapshot_name: str) -> bool:
    """Save emulator snapshot using adb emu command."""
    print(f"\nSaving emulator snapshot: {snapshot_name}")

    try:
        result = subprocess.run(
            ["adb", "emu", "avd", "snapshot", "save", snapshot_name],
            capture_output=True,
            text=True,
            timeout=120  # 2 minutes timeout
        )
        print(result.stdout)
        if result.stderr:
            print(f"STDERR: {result.stderr}")

        if result.returncode != 0:
            print(f"ERROR: Snapshot save failed with return code {result.returncode}")
            return False

        print(f"Snapshot '{snapshot_name}' saved successfully")
        return True

    except subprocess.TimeoutExpired:
        print("ERROR: Snapshot save timed out after 2 minutes")
        return False
    except Exception as e:
        print(f"ERROR: Failed to save snapshot: {e}")
        return False


def load_emulator_snapshot(snapshot_name: str) -> bool:
    """Load emulator snapshot using adb emu command."""
    print(f"\nLoading emulator snapshot: {snapshot_name}")

    try:
        result = subprocess.run(
            ["adb", "emu", "avd", "snapshot", "load", snapshot_name],
            capture_output=True,
            text=True,
            timeout=180  # 3 minutes timeout
        )
        print(result.stdout)
        if result.stderr:
            print(f"STDERR: {result.stderr}")

        if result.returncode != 0:
            print(f"ERROR: Snapshot load failed with return code {result.returncode}")
            return False

        print(f"Snapshot '{snapshot_name}' loaded successfully")
        return True

    except subprocess.TimeoutExpired:
        print("ERROR: Snapshot load timed out after 3 minutes")
        return False
    except Exception as e:
        print(f"ERROR: Failed to load snapshot: {e}")
        return False


def snapshot_exists(snapshot_name: str) -> bool:
    """Check if a snapshot already exists in the emulator."""
    try:
        result = subprocess.run(
            ["adb", "emu", "avd", "snapshot", "list"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            # Parse the output to find snapshot names
            for line in result.stdout.splitlines():
                # Snapshot list format: ID NAME SIZE DATE TIME CLOCK (e.g., "--  snapshot_base  395M  ...")
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1] == snapshot_name:
                    return True
        return False
    except Exception as e:
        print(f"WARNING: Failed to check snapshot existence: {e}")
        return False


def install_apps(apk_dir: str) -> bool:
    """Install all APKs from the specified directory to emulator."""
    print(f"\nInstalling apps from: {apk_dir}")

    # Check if directory exists
    if not os.path.isdir(apk_dir):
        print(f"ERROR: APK directory not found: {apk_dir}")
        return False

    # Find all APK files
    apks = []
    for root, dirs, files in os.walk(apk_dir):
        for f in files:
            if f.lower().endswith(".apk"):
                apks.append(os.path.join(root, f))

    if not apks:
        print(f"WARNING: No APK files found in {apk_dir}")
        return False

    print(f"Found {len(apks)} APK files")

    success_count = 0
    failed_count = 0

    for apk_path in apks:
        apk_name = os.path.basename(apk_path)
        print(f"Installing {apk_name} ...")

        try:
            result = subprocess.run(
                ["adb", "install", "-r", "-d", apk_path],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0 and "Success" in result.stdout:
                print("  Success")
                success_count += 1
            else:
                print("  Failed")
                if result.stderr:
                    for line in result.stderr.strip().splitlines():
                        if line.strip():
                            print(f"    {line.strip()}")
                failed_count += 1
        except Exception as e:
            print(f"  Error: {e}")
            failed_count += 1

    print(f"\nInstall complete: {success_count} success, {failed_count} failed")
    return failed_count == 0


def setup_installed_apps(console_port: int = 5554, adb_path: str = "adb") -> bool:
    """Setup installed apps (initialize apps, handle first-run popups, etc.)."""
    print(f"\nSetting up installed apps...")

    try:
        # Suppress logging from android_world
        logging.getLogger("android_world").setLevel(logging.WARNING)

        # Create controller and environment
        controller = android_world_controller.get_controller(
            console_port=console_port,
            adb_path=adb_path,
        )
        env = interface.AsyncAndroidEnv(controller)

        # Import apps list to print which apps will be setup
        from android_world.env.setup_device import apps as setup_apps_module
        from android_world.env.setup_device import setup as setup_module

        print(f"Apps to setup: {[app.app_name for app in setup_module._APPS]}")

        # Setup apps (this handles first-run initialization)
        setup.setup_apps(env)

        print("App setup completed successfully")
        return True

    except Exception as e:
        print(f"ERROR: Failed to setup apps: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Batch restore app data and create emulator snapshots"
    )
    parser.add_argument(
        "--install-apps",
        action="store_true",
        help="Install apps from APK directory before restoring data"
    )
    parser.add_argument(
        "--apk-dir",
        type=str,
        default="./apks",
        help="Directory containing APK files (default: ./apks)"
    )
    parser.add_argument(
        "--console-port",
        type=int,
        default=5554,
        help="Android emulator console port (default: 5554)"
    )
    parser.add_argument(
        "--adb-path",
        type=str,
        default="adb",
        help="Path to adb binary (default: adb)"
    )
    parser.add_argument(
        "--only-install-apps",
        action="store_true",
        help="Only install apps, setup apps, and save clean snapshot (skip data restore)"
    )
    args = parser.parse_args()

    print("="*60)
    print("Batch Restore and Snapshot Tool")
    print("="*60)

    CLEAN_SNAPSHOT_NAME = "snapshot_base"  # Clean snapshot with initialized apps

    # Step 1: Optionally install apps and setup (initialize apps, handle first-run popups)
    if args.install_apps:
        apk_dir = os.path.join(BASE_DIR, args.apk_dir)
        if not install_apps(apk_dir):
            print("WARNING: App installation failed, continuing anyway...")

        # Setup apps after installation (initialize apps, handle first-run popups)
        if not setup_installed_apps(
            console_port=args.console_port,
            adb_path=args.adb_path
        ):
            print("ERROR: App setup failed, exiting...")
            sys.exit(1)

        # Step 1.5: Go to home screen before saving snapshot
        print("\nGoing to home screen...")
        try:
            subprocess.run(
                ["adb", "shell", "input", "keyevent", "KEYCODE_HOME"],
                capture_output=True,
                timeout=10
            )
            print("Home screen ready")
        except Exception as e:
            print(f"Warning: Failed to go to home screen: {e}")

        # Step 2: Save clean snapshot (with initialized apps)
        print("\n" + "="*60)
        print("Saving clean snapshot with initialized apps...")
        print("="*60)
        if not save_emulator_snapshot(CLEAN_SNAPSHOT_NAME):
            print("ERROR: Failed to save clean snapshot, exiting...")
            sys.exit(1)

        # If --only-install-apps is specified, stop here (only do app installation and setup)
        if args.only_install_apps:
            print("\n" + "="*60)
            print("Only-install-apps mode: installed apps and saved clean snapshot")
            print("="*60)
            sys.exit(0)

    # Check if operated_app_data exists
    if not os.path.exists(OPERATED_APP_DATA_DIR):
        print(f"ERROR: Directory not found: {OPERATED_APP_DATA_DIR}")
        sys.exit(1)

    # Get data directories
    data_dirs = get_data_dirs()
    if not data_dirs:
        print(f"ERROR: No data directories found in {OPERATED_APP_DATA_DIR}")
        sys.exit(1)

    print(f"\nFound {len(data_dirs)} data directories:")
    for d in data_dirs:
        print(f"  - {os.path.relpath(d, OPERATED_APP_DATA_DIR)}")

    # Process each data directory
    for data_dir in data_dirs:
        # Extract user number and category from path (e.g., user_0/short -> 0, short)
        rel_path = os.path.relpath(data_dir, OPERATED_APP_DATA_DIR)
        parts = rel_path.split(os.sep)
        user_num = parts[0].split("_")[-1]
        category = parts[1]
        snapshot_name = f"snapshot_{user_num}_{category}"

        print(f"\n{'#'*60}")
        print(f"# Processing {rel_path}")
        print(f"{'#'*60}")

        # Check if snapshot already exists
        if snapshot_exists(snapshot_name):
            print(f"Snapshot '{snapshot_name}' already exists, skipping...")
            continue

        # Step 3: Load clean snapshot (restore initialized apps state)
        if not load_emulator_snapshot(CLEAN_SNAPSHOT_NAME):
            print(f"WARNING: Failed to load clean snapshot for {data_dir}, continuing without it...")

        # Step 4: Restore data to emulator
        if not restore_app_data(data_dir):
            print(f"WARNING: Restore failed for {data_dir}, skipping...")
            continue

        # Step 5: Save emulator snapshot
        if not save_emulator_snapshot(snapshot_name):
            print(f"WARNING: Snapshot failed for {data_dir}, continuing...")

    print("\n" + "="*60)
    print("All tasks completed!")
    print("Snapshots are saved in the AVD directory")
    print("="*60)


if __name__ == "__main__":
    main()