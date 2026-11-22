#!/usr/bin/env python3
"""Validate the *portable PING engine*, not the DSi Wi-Fi hardware.
No ROM, SD contents, user save or Android connection is used.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root=Path(__file__).resolve().parents[2]
engine=root/"core/bootstrap/retail/nettransport"
common=root/"core/bootstrap/retail/common/include"
test=root/"tests/v72_host/test_ping.c"
compiler=os.environ.get("CC") or shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
if not compiler:
    sys.exit("A native C compiler is required. Set CC if necessary.")
with tempfile.TemporaryDirectory(prefix="pw_v72_ping_") as tmp:
    exe=Path(tmp)/("pw_ping.exe" if os.name=="nt" else "pw_ping")
    cmd=[compiler,"-std=c11","-O2","-Wall","-Wextra","-Werror",
         "-Wno-unused-function","-I",str(engine),"-I",str(common),
         str(test),str(engine/"walker_ping_engine.c"),"-o",str(exe)]
    print("Compiling offline V7.2 PING state machine...",flush=True)
    subprocess.run(cmd,check=True)
    subprocess.run([str(exe)],check=True)
