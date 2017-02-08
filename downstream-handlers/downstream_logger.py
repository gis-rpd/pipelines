#!/usr/bin/env python3
"""MongoDB status updates for the downstream pipeline
"""
# standard library imports
import logging
import sys
import os
import argparse
import getpass

#--- third party imports
# WARN: need in conda root and snakemake env
import pymongo
from bson.objectid import ObjectId

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from pipelines import generate_timestamp
from mongodb import mongodb_conn

__author__ = "Lavanya Veeravalli"
__email__ = "veeravallil@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)

def main():
    """main function"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-d', "--db-id",
                        help="DB id", required=True,)
    parser.add_argument('-o', "--outdir",
                        help="out directory", required=True)
    parser.add_argument('-m', "--mode",
                        help="mode", required=True,
                        choices=['start', 'check'])
    parser.add_argument('-t', "--test_server", action='store_true')
    parser.add_argument('-n', "--dry-run", action='store_true',
                        help="Dry run")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Increase verbosity")
    parser.add_argument('-q', '--quiet', action='count', default=0,
                        help="Decrease verbosity")
    args = parser.parse_args()

    # Repeateable -v and -q for setting logging level.
    # See https://www.reddit.com/r/Python/comments/3nctlm/what_python_tools_should_i_be_using_on_every/
    # and https://gist.github.com/andreas-wilm/b6031a84a33e652680d4
    # script -vv -> DEBUG
    # script -v -> INFO
    # script -> WARNING
    # script -q -> ERROR
    # script -qq -> CRITICAL
    # script -qqq -> no logging at all
    logger.setLevel(logging.WARN + 10*args.quiet - 10*args.verbose)

    user_name = getpass.getuser()
    if user_name != "userrig":
        logger.warning("Not a production user. Skipping MongoDB update")
        sys.exit(0)
    _id = args.db_id
    connection = mongodb_conn(args.test_server)
    if connection is None:
        sys.exit(1)
    logger.info("Database connection established")
    db = connection.gisds.pipeline_runs
    if args.mode == "start":
        #Check if 'run' and 'outdir' does not exists
        results = db.find({"_id":ObjectId(args.db_id), "run":{"$exists": False}, \
            "outdir":{"$exists": False}})
        if results.count() == 1:
            logger.info("Starting the analysis")
            try:
                if not args.dry_run:
                    start_time = generate_timestamp()
                    db.update({"_id": ObjectId(args.db_id)},
                        {"$set":
                            {"outdir": args.outdir,
                                "run": {
                                    "start_time" : start_time,
                                    "status" : "STARTED"
                        }}})
            except pymongo.errors.OperationFailure:
                logger.fatal("mongoDB OperationFailure")
                sys.exit(0)
        else:
            #Check if 'run.start_time' and 'outdir' exists
            results = db.find({"_id":ObjectId(args.db_id), "run.start_time":{"$exists": True}, \
             "outdir":{"$exists": True}})
            if results.count() == 1:
                logger.info("Re-running the analysis")
                try:
                    if not args.dry_run:
                        start_time = generate_timestamp()
                        db.update({"_id": ObjectId(args.db_id)},
                            {"$set":
                                {"run.status": "RESTART"    
                            }})
                        db.update({"_id": ObjectId(args.db_id)},
                                {"$inc":{"run.num_restarts": 1}
                            })
                except pymongo.errors.OperationFailure:
                    logger.fatal("mongoDB OperationFailure")
                    sys.exit(0)
    elif args.mode == "check":
        logger.info("Checking snakemake logs for completion time and status")
        #FIXME check the status and endtime
    else:
        raise ValueError(args.mode)
    # close the connection to MongoDB
    connection.close()

if __name__ == "__main__":
    logger.info("MongoDB status update starting")
    main()
    logger.info("Successful program exit")
