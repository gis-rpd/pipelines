#!/usr/bin/env python3
"""Pretty print all MongoDB (runcomplete) entries
"""

# standard library imports
#
import sys
import os
import pprint
import argparse

# third party imports
#
#/

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from pipelines import generate_window
# FIXME: that function should go into lib
sys.path.insert(0, os.path.join(LIB_PATH, "..", "bcl2fastq"))
from mongo_status import mongodb_conn


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


def main():
    """main function"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-t', "--testing", action='store_true',
                        help="Use MongoDB test-server")
    default = 7
    parser.add_argument('-w', '--win', type=int, default=default,
                        help="Number of days to look back (default {})".format(default))
    args = parser.parse_args()

    pp = pprint.PrettyPrinter(indent=2)

    connection = mongodb_conn(args.testing)
    db = connection.gisds.runcomplete
    epoch_present, epoch_back = generate_window(args.win)
    results = db.find({"analysis.Status": "SUCCESS",
                       "timestamp": {"$gt": epoch_back, "$lt": epoch_present}})
    for record in results:
        pp.pprint(record)


if __name__ == "__main__":
    main()
