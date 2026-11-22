#!/usr/bin/env python3
"""Cross-language handshake fixture with actual Android DirectSyncProtocol.
Standalone JVM + C compiler only; no Android SDK or phone necessary.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root=Path(__file__).resolve().parents[2]
tests=Path(__file__).resolve().parent
android=root/"core/android/app/src/main/java/io/github/sdtransporter/pokewalker/DirectSyncProtocol.java"
engine=root/"core/bootstrap/retail/nettransport"
common=root/"core/bootstrap/retail/common/include"
cc=os.getenv("CC") or shutil.which("cc") or shutil.which("gcc")
javac=shutil.which("javac")
java=shutil.which("java")
if not (cc and javac and java):
    sys.exit("Interop test needs C compiler plus JDK javac/java")
if not android.is_file():
    sys.exit("Missing real Android DirectSyncProtocol.java")
with tempfile.TemporaryDirectory(prefix="pw_v72_interop_") as tmp:
    tmp=Path(tmp)
    executable=tmp/("ping_interop.exe" if os.name=="nt" else "ping_interop")
    subprocess.run([cc,"-std=c11","-O2","-Wall","-Wextra","-Werror",
                    "-Wno-unused-function","-I",str(engine),"-I",str(common),
                    str(tests/"ping_interop.c"),str(engine/"walker_ping_engine.c"),
                    "-o",str(executable)],check=True)
    subprocess.run([javac,"-d",str(tmp),str(android),
                    str(tests/"DirectSyncInteropTest.java")],check=True)
    req=tmp/"request.bin";reply=tmp/"response.bin"
    subprocess.run([str(executable),"request",str(req)],check=True)
    subprocess.run([java,"-cp",str(tmp),
                    "io.github.sdtransporter.pokewalker.DirectSyncInteropTest",
                    str(req),str(reply)],check=True)
    subprocess.run([str(executable),"response",str(reply)],check=True)
