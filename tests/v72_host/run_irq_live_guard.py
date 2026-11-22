#!/usr/bin/env python3
"""V7.2.6 NTR RAM read-boundary tests; no real memory reads."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root=Path(__file__).resolve().parents[2]
cc=os.environ.get("CC") or shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
if not cc: sys.exit("A native C compiler is required")
with tempfile.TemporaryDirectory(prefix="pw_v726_irq_read_") as td:
    out=Path(td)/("irq_read.exe" if os.name=="nt" else "irq_read")
    subprocess.run([cc,"-std=c11","-O2","-Wall","-Wextra","-Werror",
                    "-I",str(root/"core/bootstrap/retail/common/include"),
                    str(root/"tests/v72_host/test_irq_live_guard.c"),
                    "-o",str(out)],check=True)
    subprocess.run([str(out)],check=True)
