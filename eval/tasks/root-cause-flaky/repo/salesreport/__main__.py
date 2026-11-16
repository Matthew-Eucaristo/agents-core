import argparse
import sys

from salesreport.orders import CsvOrderSource
from salesreport.service import ReportService


def main(argv=None):
    parser = argparse.ArgumentParser(prog="salesreport", description="Print the sales summary for an orders export.")
    parser.add_argument("orders_csv")
    args = parser.parse_args(argv)
    service = ReportService(CsvOrderSource(args.orders_csv))
    print(service.text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
