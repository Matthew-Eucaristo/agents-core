import json
import pathlib
import sys

cell = pathlib.Path(sys.argv[1])
expected = "MARKER-42" if (cell / "home" / ".agents" / "AGENTS.md").exists() else "NONE"
done = cell / "repo" / "done.txt"
found = done.read_text().strip() if done.exists() else None
print(json.dumps({"checks": {"marker_written": found == expected}, "notes": f"expected {expected}, found {found}"}))
