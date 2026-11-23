#!/usr/bin/env python3
"""Compile and execute SDK-free V7.1 sanity tests with a host C compiler.

This verifies data layouts and the fail-closed resolver. It CANNOT validate
ARM7/ARM9 ABI, firmware behavior, Wi-Fi, or a physical DSi.
"""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
testdir = Path(__file__).resolve().parent
source = root / "core/bootstrap/retail/common/source/walker_hgss_net.c"
headers = root / "core/bootstrap/retail/common/include"
cc = os.environ.get("CC") or shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
if not cc:
    sys.exit("ERROR: no C compiler found (set CC to gcc, clang, or another host C compiler).")

with tempfile.TemporaryDirectory(prefix="walker_v71_") as tmp:
    exe = Path(tmp) / ("v71_host.exe" if os.name == "nt" else "v71_host")
    cmd = [cc, "-std=c11", "-O2", "-Wall", "-Wextra",
           "-Wno-unused-function", "-I", str(testdir), "-I", str(headers),
           str(testdir / "test_net.c"), str(source), "-o", str(exe)]
    print("Compiling V7.1 SDK-free host checks...", flush=True)
    subprocess.run(cmd, check=True)
    subprocess.run([str(exe)], check=True)
    print("Compiling and executing V7.7 fixed-window CRC32 host vectors...", flush=True)
    sigdir = root / "core/bootstrap/retail/cardenginei/arm9_igm"
    shaexe = Path(tmp) / ("v77_sha.exe" if os.name == "nt" else "v77_sha")
    subprocess.run([cc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-DB4DS",
                    "-I", str(sigdir / "include"),
                    str(testdir / "test_v77_wifi_sha_host.c"),
                    str(sigdir / "source/walker_arm9_wifi_sig.c"),
                    "-o", str(shaexe)], check=True)
    subprocess.run([str(shaexe)], check=True)
    print("Running synthetic identity and source wiring checks...", flush=True)
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(testdir),
                    "-p", "test_*.py"], check=True)
