"""Write an adjacent SHA256 checksum using only the archive basename."""
import hashlib
from pathlib import Path
import sys

path = Path(sys.argv[1])
digest = hashlib.sha256(path.read_bytes()).hexdigest()
path.with_name(path.name + ".sha256").write_text(f"{digest}  {path.name}\n")
