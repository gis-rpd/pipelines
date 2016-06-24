#!/usr/bin/env python3
"""
Retrieves runcomplete records in MongoDB with user-specified parameters for filtering.
Unless specified by -w or --win, only the 7 most recent days of records are retrieved.
"""

#--- standard library imports
#
from argparse import ArgumentParser
import os
from pprint import PrettyPrinter
import sys

#--- third-party imports
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


def instantiate_args():
    """
    Instantiates argparse object
    """
    instance = ArgumentParser(description=__doc__)
    instance.add_argument("-t", "--testing", action="store_true", help="use MongoDB test-server")
    instance.add_argument(
        "-s", "--status", help="filter records by analysis status (STARTED/FAILED/SUCCESS)")
    instance.add_argument("-m", "--mux", help="filter records by mux_id")
    instance.add_argument("-r", "--run", help="filter records by run")
    instance.add_argument("-w", "--win", type=int, help="filter records up to specified day(s) ago")
    return instance.parse_args()


def instantiate_mongo(testing):
    """
    Instantiates MongoDB database object
    """
    return mongodb_conn(testing).gisds.runcomplete


def instantiate_query(args):
    """
    Instantiates MongoDB query dictionary object
    """
    instance = {}
    if args.status:
        instance["analysis.Status"] = args.status
    if args.mux:
        instance["analysis.per_mux_status.mux_id"] = args.mux
    if args.run:
        instance["run"] = args.run
    if args.win:
        epoch_present, epoch_initial = generate_window(args.win)
    else:
        epoch_present, epoch_initial = generate_window(7)
    instance["timestamp"] = {"$gt": epoch_initial, "$lt": epoch_present}
    return instance


def main():
    """
    Main function
    """
    args = instantiate_args()
    mongo = instantiate_mongo(args.testing)
    query = instantiate_query(args)

    for record in mongo.find(query):
        PrettyPrinter(indent=2).pprint(record)

if __name__ == "__main__":
    main()
