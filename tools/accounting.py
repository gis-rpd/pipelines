#!/usr/bin/env python3
"""
collection: gisds.accountinglogs
"""

#--- standard library imports
#
from argparse import ArgumentParser
from datetime import datetime
import os
from pprint import PrettyPrinter
import sys
from time import gmtime, strftime


#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from mongodb import mongodb_conn


__author__ = "LIEW Jun Xian"
__email__ = "liewjx@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


def main():
    """
    Main function
    """
    instance = ArgumentParser(description=__doc__)
    instance.add_argument("-j", "--jobNo", help="filter records by jobNo of jobs")
    instance.add_argument("-o", "--owner", help="filter records by owner of jobs")
    args = instance.parse_args()

    selection = {}
    if args.jobNo:
        selection["jobs.jobNo"] = args.jobNo
    if args.owner:
        selection["jobs.owner"] = args.owner

    projection = {}
    projection["jobs"] = 1

#    print("SELECTION:\t" + str(selection))
#    print("PROJECTION:\t" + str(projection))

    for document in mongodb_conn(False).gisds.accountinglogs.find(selection, projection):
        for job in document["jobs"]:
            if job["jobNo"] == args.jobNo:
                job["ruWallClock"] = strftime("%Hh%Mm%Ss", gmtime(job["ruWallClock"]))
                job["submissionTime"] = str(datetime.fromtimestamp(
                    job["submissionTime"]).isoformat()).replace(":", "-")
                PrettyPrinter(indent=2).pprint(job)


if __name__ == "__main__":
    main()
