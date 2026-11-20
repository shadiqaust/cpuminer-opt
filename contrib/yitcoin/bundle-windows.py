"""Copy the complete MinGW DLL closure; never copy Windows system DLLs."""
from pathlib import Path
import re
import shutil
import subprocess
import sys

dest = Path(sys.argv[1])
text = Path(sys.argv[2]).read_text()
if "not found" in text.lower():
    raise RuntimeError("An unresolved dependency was reported:\n" + text)
count = 0
for line in text.splitlines():
    match = re.search(r"=>\s+(.+?\.dll)\s+\(", line, re.IGNORECASE)
    if not match:
        continue
    windows_path = match.group(1).strip()
    # Only redistribute MinGW libraries, not DLLs supplied by Windows itself.
    normalized = windows_path.replace("\\", "/").lower()
    if "/mingw64/" not in normalized:
        continue
    native_path = subprocess.check_output(["cygpath", "-m", windows_path], text=True).strip()
    source = Path(native_path)
    shutil.copy2(source, dest / source.name)
    count += 1
if not count:
    raise RuntimeError("No MinGW runtime DLLs were found; refusing an incomplete ZIP.")
print(f"Bundled {count} runtime DLL entries.")
