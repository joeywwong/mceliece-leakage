"""Invalidate objects when compiler identity or flags change, without needless rebuilds."""
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

path, compiler, flags = sys.argv[1:]
command = shlex.split(compiler)
config = json.dumps({
    "command": command, "executable": shutil.which(command[0]), "flags": flags,
    "version": subprocess.check_output(command + ["--version"], text=True),
    "target": subprocess.check_output(command + ["-dumpmachine"], text=True),
}, sort_keys=True, indent=2) + "\n"
path = Path(path)
if not path.exists() or path.read_text() != config:
    path.write_text(config)
