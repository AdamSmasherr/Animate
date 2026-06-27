#!/usr/bin/env python3
"""
Build a versioned, installable zip of the AMP_AniMatePro addon.

The version is 1.<git commit count> to match the release scheme used by the CI
in .github/workflows/release.yml. The zip contains the AMP_AniMatePro folder at
its top level, so it installs through Preferences > Add-ons > Install from Disk.

Usage:  python build.py
Output: dist/AMP_AniMatePro_v1.<n>.zip
"""

import os
import subprocess
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = "AMP_AniMatePro"


def version():
    try:
        n = subprocess.check_output(
            ["git", "rev-list", "--count", "HEAD"], cwd=HERE
        ).decode().strip()
        return "1." + n
    except Exception:
        return "1.0"


def build():
    ver = version()
    out_dir = os.path.join(HERE, "dist")
    os.makedirs(out_dir, exist_ok=True)
    zip_path = os.path.join(out_dir, f"{ADDON}_v{ver}.zip")
    root = os.path.join(HERE, ADDON)

    count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for f in filenames:
                if f.endswith((".pyc", ".pyo")):
                    continue
                full = os.path.join(dirpath, f)
                arc = os.path.relpath(full, HERE).replace("\\", "/")
                z.write(full, arc)
                count += 1

    print(f"Built {zip_path} ({count} files)")
    return zip_path


if __name__ == "__main__":
    build()
