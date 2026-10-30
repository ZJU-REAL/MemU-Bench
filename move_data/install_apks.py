#!/usr/bin/env python3
"""
Cross-platform: Auto install all APKs in a directory
Works on both Mac and Windows
Usage: python install_apks.py [apk_directory]
"""

import os
import sys
import subprocess


def adb(*args):
    """Run adb command, return CompletedProcess with decoded output."""
    result = subprocess.run(["adb"] + list(args), capture_output=True)
    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")
    return subprocess.CompletedProcess(
        args=result.args, returncode=result.returncode,
        stdout=stdout, stderr=stderr,
    )


def find_apks(directory):
    """Recursively find all .apk files in directory."""
    apks = []
    for root, dirs, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(".apk"):
                apks.append(os.path.join(root, f))
    return sorted(apks)


def main():
    apk_dir = sys.argv[1] if len(sys.argv) > 1 else "./apks"

    print("========== Auto Install APKs ==========")
    print(f"APK directory: {apk_dir}")
    print()

    # Check if directory exists
    if not os.path.isdir(apk_dir):
        print(f"Error: Directory {apk_dir} does not exist")
        sys.exit(1)

    # Find all APK files
    apks = find_apks(apk_dir)
    if not apks:
        print(f"Error: No APK files found in {apk_dir}")
        sys.exit(1)

    print(f"Found {len(apks)} APK files")
    print()

    # Install each APK
    success_count = 0
    failed_count = 0

    for apk_path in apks:
        apk_name = os.path.basename(apk_path)
        print(f"Installing {apk_name} ...")

        # Try to install, allow version downgrade (-r -d)
        result = adb("install", "-r", "-d", apk_path)
        if result.returncode == 0 and "Success" in result.stdout:
            print("  Success")
            success_count += 1
        else:
            print("  Failed")
            # Show error details
            for line in result.stderr.strip().splitlines():
                if line.strip():
                    print(f"    {line.strip()}")
            failed_count += 1
        print()

    print("========== Install Complete ==========")
    print(f"Success: {success_count}")
    print(f"Failed: {failed_count}")
    print()

    # Show installed packages
    print("Installed third-party packages:")
    result = adb("shell", "pm list packages -3")
    for line in result.stdout.strip().splitlines():
        pkg = line.strip().split(":", 1)[-1]
        if pkg:
            print(f"  {pkg}")


if __name__ == "__main__":
    main()