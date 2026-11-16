import argparse
import sys

from .errors import DropError
from .manifest import load_manifest, write_manifest
from .transfer import receive


def build_parser():
    parser = argparse.ArgumentParser(prog="dropline", description="Pull files out of a drop spool.")
    commands = parser.add_subparsers(dest="command", required=True)
    index = commands.add_parser("index", help="write the manifest for a spool directory")
    index.add_argument("spool")
    listing = commands.add_parser("list", help="show the files a spool offers")
    listing.add_argument("spool")
    fetch = commands.add_parser("fetch", help="copy files out of a spool and verify them")
    fetch.add_argument("spool")
    fetch.add_argument("names", nargs="+")
    fetch.add_argument("--to", dest="dest", default=".")
    fetch.add_argument("--overwrite", action="store_true")
    return parser


def main(argv=None, stdout=None, stderr=None):
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    args = build_parser().parse_args(argv)
    try:
        if args.command == "index":
            count = write_manifest(args.spool)
            print(f"indexed {count} file{'' if count == 1 else 's'}", file=stdout)
        elif args.command == "list":
            for entry in load_manifest(args.spool).values():
                print(f"{entry.size:>10}  {entry.name}", file=stdout)
        else:
            for name in args.names:
                target = receive(args.spool, name, args.dest, overwrite=args.overwrite)
                print(f"received {target}", file=stdout)
    except DropError as exc:
        print(f"error: {exc}", file=stderr)
        return exc.exit_code
    return 0
