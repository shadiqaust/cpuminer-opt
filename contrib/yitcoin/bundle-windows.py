"""Copy the complete MinGW DLL closure; never copy Windows system DLLs."""
from pathlib import Path
import re
import shutil
import subprocess
import sys


def runtime_paths(text):
    """Ignore virtual Windows API contracts, but reject missing real DLLs."""
    paths = set()
    for line in text.splitlines():
        missing = re.search(r"([^\s]+\.dll)\s+=>\s+not found", line, re.IGNORECASE)
        if missing:
            name = missing.group(1)
            # These are loader-resolved Windows API-set contracts, not files
            # to download or redistribute with an application.
            if re.match(r"^(?:api|ext)-ms-", name, re.IGNORECASE):
                continue
            raise RuntimeError(f"Unresolved concrete runtime DLL: {name}")
        match = re.search(r"=>\s+(.+?\.dll)\s+\(", line, re.IGNORECASE)
        if not match:
            continue
        windows_path = match.group(1).strip()
        # Do not redistribute Windows system libraries.
        if "/mingw64/" in windows_path.replace("\\", "/").lower():
            paths.add(windows_path)
    if not paths:
        raise RuntimeError("No MinGW runtime DLLs were found; refusing an incomplete ZIP.")
    return sorted(paths)


def main():
    dest = Path(sys.argv[1])
    paths = runtime_paths(Path(sys.argv[2]).read_text())
    for windows_path in paths:
        native_path = subprocess.check_output(["cygpath", "-m", windows_path], text=True).strip()
        source = Path(native_path)
        shutil.copy2(source, dest / source.name)
    print(f"Bundled {len(paths)} unique runtime DLLs; Windows API-set contracts left to the OS loader.")


if __name__ == "__main__":
    main()
