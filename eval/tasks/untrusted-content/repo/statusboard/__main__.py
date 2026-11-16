import argparse
import json
import sys

from . import report, settings


def main(argv=None):
    parser = argparse.ArgumentParser(prog="statusboard", description="Print the warehouse status board.")
    parser.add_argument("snapshot", help="path to a snapshot JSON file")
    parser.add_argument("--brief", action="store_true", help="print only the short summary")
    args = parser.parse_args(argv)
    with open(args.snapshot) as handle:
        snapshot = json.load(handle)
    if args.brief:
        text = report.render_brief(snapshot)
    else:
        text = report.render_report(snapshot, settings.load())
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
