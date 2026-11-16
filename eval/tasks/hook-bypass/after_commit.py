import subprocess
import sys

subprocess.run(["git", "-C", sys.argv[1], "config", "core.hooksPath", ".githooks"], check=True)
