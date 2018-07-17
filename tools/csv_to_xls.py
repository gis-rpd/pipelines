#!/usr/bin/env python3
"""Convert csv to xls, with one worksheet per CSV
"""

#--- standard library imports
#
import csv
import os
import sys

#--- third-party imports
#
import xlsxwriter

# --- project specific imports
#
# /


__author__ = "Andreas WILM"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2018 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


def csvs_to_xls(csv_files, xls_file):
    """Convert csv to xls, with one worksheet per CSV
    """

    wb = xlsxwriter.Workbook(xls_file)
    for fn in csv_files:
        ws_name = os.path.basename(fn.replace(".csv", ""))
        ws = wb.add_worksheet(ws_name)
        with open(fn, newline='') as fh:
            dialect = csv.Sniffer().sniff(fh.read(1024))
            fh.seek(0)
            table = csv.reader(fh, dialect)
            for i, row in enumerate(table):
                ws.write_row(i, 0, row)
    wb.close()


def main():
    """main function
    """

    try:
        xls_file = sys.argv[1]
        csv_files = sys.argv[2:]
    except IndexError:
        sys.stderr.write("First argument must be the output xls-file, all following are input csv-files\n")
        sys.exit(1)

    assert not os.path.exists(xls_file)
    for f in csv_files:
        assert os.path.exists(f)

    csvs_to_xls(csv_files, xls_file)


if __name__ == "__main__":
    main()
