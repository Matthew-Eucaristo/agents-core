import pathlib
import shutil
import sys

WIP = pathlib.Path(__file__).resolve().parent / "wip"


def main():
    repo = pathlib.Path(sys.argv[1]).resolve()
    for source in sorted(WIP.rglob("*")):
        if not source.is_file() or "__pycache__" in source.parts:
            continue
        target = repo / source.relative_to(WIP)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


if __name__ == "__main__":
    main()
