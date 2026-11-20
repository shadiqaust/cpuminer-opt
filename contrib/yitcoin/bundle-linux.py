"""Bundle non-glibc dependencies and make their lookup relative to the miner."""
from pathlib import Path
import re
import shutil
import subprocess
import sys

dest = Path(sys.argv[1]).resolve()
binary = dest / "cpuminer"
output = subprocess.check_output(["ldd", str(binary)], text=True)
if "not found" in output:
    raise RuntimeError(output)
# glibc and its loader must come from the target operating system.
system = re.compile(r"^(libc\.so|libm\.so|libpthread\.so|libdl\.so|librt\.so|libresolv\.so|libutil\.so|ld-linux)")
libraries = []
for line in output.splitlines():
    match = re.search(r"=>\s+(/\S+)", line)
    if not match:
        continue
    source = Path(match.group(1))
    if system.match(source.name):
        continue
    target = dest / "lib" / source.name
    shutil.copy2(source, target)
    libraries.append(target)
for path in libraries:
    subprocess.run(["patchelf", "--set-rpath", "$ORIGIN", str(path)], check=True)
subprocess.run(["patchelf", "--set-rpath", "$ORIGIN/lib", str(binary)], check=True)
subprocess.run(["ldd", str(binary)], check=True)
