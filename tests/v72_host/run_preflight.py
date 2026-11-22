#!/usr/bin/env python3
"""Portable gate tests only; no device or DSWifi radio initialization."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root=Path(__file__).resolve().parents[2]
base=root/"core/bootstrap/retail/nettransport"
cc=os.environ.get("CC") or shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
if not cc:
    sys.exit("A native C compiler is required")
with tempfile.TemporaryDirectory(prefix="pw_v72_wifi_gate_") as t:
    exe=Path(t)/("preflight.exe" if os.name=="nt" else "preflight")
    subprocess.run([cc,"-std=c11","-O2","-Wall","-Wextra","-Werror",
                    "-I",str(base),str(root/"tests/v72_host/test_wifi_preflight.c"),
                    str(base/"walker_wifi_preflight.c"),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
