#!/usr/bin/env python3
"""Build and exercise structural NTR IRQ_WIFI slot-24 footprint checking."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root=Path(__file__).resolve().parents[2]
src=root/"core/bootstrap/retail/nettransport"
cc=os.getenv("CC") or shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
if not cc:
    sys.exit("No native C compiler available")
with tempfile.TemporaryDirectory(prefix="pw_irq_wifi_audit_") as tmp:
    exe=Path(tmp)/("irq_audit.exe" if os.name=="nt" else "irq_audit")
    cmd=[cc,"-std=c11","-O2","-Wall","-Wextra","-Werror",
         "-I",str(src),str(root/"tests/v72_host/test_wifi_irq_audit.c"),
         str(src/"walker_wifi_irq_audit.c"),"-o",str(exe)]
    subprocess.run(cmd,check=True)
    subprocess.run([str(exe)],check=True)
