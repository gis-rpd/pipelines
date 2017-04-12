#!/usr/bin/env python3
"""FIXME:add-doc
"""


#--- standard library imports
#
from argparse import ArgumentParser
from datetime import date
from hashlib import md5
from os import mkdir
from os.path import abspath, dirname, exists, join, realpath
from pprint import PrettyPrinter
from shutil import move, rmtree
from sys import path
import tarfile


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
__copyright__ = "2017 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


def main():
    """
    Entry Point
    """
    instance = ArgumentParser(description=__doc__)
    instance.add_argument("-d", "--dir", required=True, help="DIR")
    instance.add_argument("-r", "--run", required=True, help="RUN")
    args = instance.parse_args()
    """
    For Test Server, testing == True
    For Production Server, testing == False
    """
    if args.dir:
        db = mongodb_conn(True).gisds.runcomplete
        for document in db.find({"run": args.run}):
    #        PrettyPrinter(indent=2).pprint(document)
            if "analysis" in document:
                PrettyPrinter(indent=2).pprint(document["analysis"][-1]["end_time"])
                last_date = list(map(int, document["analysis"][-1]["end_time"].split("T")[0].split("-")))
    #            if (date.today() - date(last_date[0], last_date[1], last_date[2])).days < 120:
                print("If last bcl2fastq < 4 months (see DB): continue")
                if exists(args.dir + "/" + get_machine_run_flowcell_id(args.run)[0] + "/" + args.run):
                    print("dir exists")
                if exists(args.dir + "/" + get_machine_run_flowcell_id(args.run)[0] + "/" + args.run + ".tar"):
                    print("tar exists")
                if exists(args.dir + "/" + get_machine_run_flowcell_id(args.run)[0] + "/" + args.run + ".tgz"):
                    print("tgz exists")

                print("If run folder does not exist: warn and continue")

                print("For all runs in DB where raw-deleted in DB is empty")
                print("CHECK CURRENT TIME STARTED:\t" + generate_timestamp())
                if "raw_deleted" not in document:
                    db.update({"_id": document["_id"]},
                              {"$push": {"raw_deleted": {"started_timestamp": generate_timestamp()}}})

                if not exists(args.dir + "/tarballs"):
                    mkdir(args.dir + "/tarballs", 0o770)
                if not exists(args.dir + "/tarballs/tmp"):
                    mkdir(args.dir + "/tarballs/tmp", 0o770)

                if exists(args.dir + "/" + get_machine_run_flowcell_id(args.run)[0] + "/" + args.run):
                    print("Tar run folder (/mnt/seq/tarballs/tmp/$run.tar) || exit 1")
                    with tarfile.open(args.dir + "/tarballs/tmp/" + args.run + ".tar", "x") as tar:
                        tar.add(args.dir + "/" + get_machine_run_flowcell_id(args.run)[0] + "/" + args.run)

                    print("Move tar from /mnt/seq/tarballs/tmp to /mnt/seq/tarballs/ || exit 1")
                    move(args.dir + "/tarballs/tmp/" + args.run + ".tar", args.dir + "/tarballs/" + args.run + ".tar")

                    print("Create md5 sum of tarball and write to tarball.md5 || exit 1")
                    md5sum = ""
                    with open(args.dir + "/tarballs/" + args.run + ".tar", "rb") as tar:
                        tarhash = md5()
                        tarhash.update(tar.read())
                        md5sum = tarhash.hexdigest()
                        print(md5sum)
                    with open(args.dir + "/tarballs/" + args.run + ".md5", "w") as md5file:
                        md5file.write(md5sum)

                    print("Delete run folder || exit 1")
                    rmtree(args.dir + "/" + get_machine_run_flowcell_id(args.run)[0] + "/" + args.run)

                    print("Set raw-deleted to done:timestamp in DB || exit 1")
                    print("CHECK CURRENT TIME DONE:\t" + generate_timestamp())

#                    if "raw_deleted" in document:
#                        print ("raw_deleted in document")
#                        if "started_timestamp" in document["raw_deleted"]:
                    start_time = ""
                    for result in db.find({"_id": document["_id"]}):
                        print(result["raw_deleted"])
                        start_time = result["raw_deleted"][0]["started_timestamp"]

                    db.update({"_id": document["_id"]},
                                {"$set":
                                    {"raw_deleted": {
                                        "started_timestamp": start_time,
                                        "done_timestamp": generate_timestamp()
                                    }
                                }
                            })


#                db.update({"_id": document["_id"]}, {"$pop": {"raw_deleted": -1}})
#                db.update({"_id": document["_id"]}, {"$unset": {"raw_deleted": -1}})
                for result in db.find({"raw_deleted": {"$exists": True}, "run": args.run}):
                    PrettyPrinter(indent=2).pprint(result)


if __name__ == "__main__":
    main()
