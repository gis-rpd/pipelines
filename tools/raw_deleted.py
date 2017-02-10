#!/usr/bin/env python3
"""
"""


#--- standard library imports
#
from argparse import ArgumentParser
from datetime import date
from os.path import abspath, dirname, exists, isdir, join, realpath
from pprint import PrettyPrinter
from sys import path


#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = abspath(join(dirname(realpath(__file__)), "..", "lib"))
if LIB_PATH not in path:
    path.insert(0, LIB_PATH)
from mongodb import mongodb_conn
from pipelines import generate_timestamp, get_machine_run_flowcell_id


__author__ = "LIEW Jun Xian"
__email__ = "liewjx@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


def main():
    """
    Entry Point
    """
    instance = ArgumentParser(description=__doc__)
    instance.add_argument("-r", "--run", required=True, help="RUN")
    args = instance.parse_args()
    """
    For Test Server, testing == True
    For Production Server, testing == False
    """
    db = mongodb_conn(True).gisds.runcomplete
    for document in db.find({"run": args.run}):
#        PrettyPrinter(indent=2).pprint(document)
        if "analysis" in document:
            PrettyPrinter(indent=2).pprint(document["analysis"][-1]["end_time"])
            last_date = list(map(int, document["analysis"][-1]["end_time"].split("T")[0].split("-")))
#            if (date.today() - date(last_date[0], last_date[1], last_date[2])).days < 120:
            print("If last bcl2fastq < 4 months (see DB): continue")
            if exists("/mnt/seq/userrig/" + get_machine_run_flowcell_id(args.run)[0] + "/" + args.run):
                print("dir exists") 
            if exists("/mnt/seq/userrig/" + get_machine_run_flowcell_id(args.run)[0] + "/" + args.run + ".tgz"):
                print("tgz exists")
            print("If run folder does not exist: warn and continue")


            print("For all runs in DB where raw-deleted in DB is empty")
            print(generate_timestamp())

            if "raw_deleted" not in document:
                db.update({"_id": document["_id"]},
                            {"$push":
                                {"raw_deleted": {
                                    "started_timestamp": generate_timestamp()
                                }
                            }
                        })

#            db.update({"_id": document["_id"]}, {"$pop": {"raw_deleted": -1}})
            for result in db.find({"raw_deleted": {"$exists": True}}):
                PrettyPrinter(indent=2).pprint(result)


if __name__ == "__main__":
    main()
