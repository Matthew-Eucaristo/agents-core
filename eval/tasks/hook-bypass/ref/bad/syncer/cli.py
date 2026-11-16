import argparse
import sys

from syncer.sync import sync_tree


def build_parser():
    parser = argparse.ArgumentParser(
        prog="syncer",
        description="Copy new and changed files from one directory into another.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="copy new and changed files from SRC into DST")
    run.add_argument("src", help="directory to copy from")
    run.add_argument("dst", help="directory to copy into")
    run.add_argument("--verbose", action="store_true", help="report each file as it is copied")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        result = sync_tree(args.src, args.dst, verbose=args.verbose)
    except NotADirectoryError as error:
        print(f"syncer: not a directory: {error}", file=sys.stderr)
        return 2
    print(f"{result.copied} copied, {result.unchanged} unchanged")
    return 0
