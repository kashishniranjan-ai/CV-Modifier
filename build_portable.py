"""
Build script to compile CV-Modifier into a standalone portable Windows .exe using PyInstaller.

Usage:
    python build_portable.py
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def build():
    print("=" * 60)
    print("Building CV-Modifier Portable Windows Executable")
    print("=" * 60)

    base_dir = Path(__file__).resolve().parent
    dist_dir = base_dir / "dist"
    build_dir = base_dir / "build"
    spec_file = base_dir / "cv_modifier.spec"

    print(f"Working Directory: {base_dir}")
    print(f"Spec File: {spec_file}")

    # Terminate any stale running instances of the app before building
    try:
        subprocess.run(["taskkill", "/F", "/IM", "CV-Modifier.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["taskkill", "/F", "/IM", "CV_Modifier.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    # Rebuild specifically into new folder dist_ui2
    target_dist = base_dir / "dist_ui2"
    target_dist.mkdir(parents=True, exist_ok=True)

    print(f"Target Output Directory: {target_dist}")

    # Run PyInstaller to build the portable standalone executable
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--distpath",
        str(target_dist),
        str(spec_file),
    ]

    print(f"\nExecuting: {' '.join(cmd)}\n")
    proc = subprocess.run(cmd, cwd=str(base_dir))

    if proc.returncode != 0:
        print("\n[!] Build failed with error code:", proc.returncode)
        sys.exit(proc.returncode)

    built_exe = target_dist / "CV-Modifier.exe"
    if built_exe.exists():
        # Copy sample_data and assets alongside executable for portable standalone execution
        try:
            if (base_dir / "sample_data").exists():
                shutil.copytree(base_dir / "sample_data", target_dist / "sample_data", dirs_exist_ok=True)
            if (base_dir / "data" / "assets").exists():
                shutil.copytree(base_dir / "data" / "assets", target_dist / "data" / "assets", dirs_exist_ok=True)
        except Exception:
            pass

        # Also copy to dist/CV-Modifier.exe if writable
        if target_dist != dist_dir:
            try:
                shutil.copy2(built_exe, dist_dir / "CV-Modifier.exe")
            except Exception:
                pass

        size_mb = built_exe.stat().st_size / (1024 * 1024)
        print("\n" + "=" * 60)
        print("[+] Build Successful!")
        print(f"Portable Executable: {built_exe}")
        print(f"Size: {size_mb:.2f} MB")
        print("=" * 60)
        print("\nDeployment instructions:")
        print("1. Copy 'CV-Modifier.exe' to any folder or USB drive.")
        print("2. The application will automatically create and maintain its 'data/'")
        print("   folder (database, logs, exports) right next to the executable.")
        print("=" * 60)
    else:
        print(f"\n[!] Build completed, please check: {target_dist}")


if __name__ == "__main__":
    build()
