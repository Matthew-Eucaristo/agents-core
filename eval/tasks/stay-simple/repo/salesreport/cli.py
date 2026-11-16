"""Command line entry point, run as: python3 -m salesreport ORDERS.json"""

import argparse
import sys

from salesreport import exporter
from salesreport.loader import load_rows


def available_formats():
    """List the format names that the exporter module offers."""
    names = []
    # Every exporter function is called to_<format>, so cut the prefix off
    for name in dir(exporter):
        if name.startswith("to_"):
            names.append(name[3:])
    return sorted(names)


def main(argv=None):
    """Run the command line and return the exit status."""
    parser = argparse.ArgumentParser(prog="salesreport", description="Print an order report.")
    parser.add_argument("path", help="JSON file with the order rows")
    parser.add_argument("--format", default="text", help="output format (default: text)")
    options = parser.parse_args(argv)

    # Find the exporter function for the requested format
    export = getattr(exporter, "to_" + options.format, None)
    if export is None:
        choices = ", ".join(available_formats())
        sys.stderr.write("unknown format %r, choose from: %s\n" % (options.format, choices))
        return 2

    # Load the rows and write the report to standard output
    try:
        rows = load_rows(options.path)
    except (OSError, ValueError) as error:
        sys.stderr.write("cannot read %s: %s\n" % (options.path, error))
        return 1
    sys.stdout.write(export(rows))
    return 0
