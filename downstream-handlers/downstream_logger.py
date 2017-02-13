#!/usr/bin/env python3
"""MongoDB status updates for the downstream pipeline
"""
# standard library imports
import logging
import sys
import os
import argparse
import getpass
from datetime import datetime

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
from pipelines import generate_timestamp, is_devel_version, send_mail
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

def dry_run_skip():
    """ skipping mongoDB updates for dry run option
    """
    logger.warning("Skipping the mongo updates")
    sys.exit(0)

def check_completion_status(results, db_id, outdir):
    """ Check if the analysis status has been updated
    """
    for record in results:
        status = record['run'].get('status', None)
        if status == "FAILED" or status == "SUCCESS":
            logger.info("Status for %s under %s has already been updated", db_id, outdir)
            sys.exit(0)

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
    if is_devel_version() or args.testing:
        mail_to = 'veeravallil'# domain added in mail function
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
                if args.dry_run:
                    dry_run_skip()
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
                sys.exit(1)
        else:
            #Check if 'run.start_time' and 'outdir' exists
            results = db.find({"_id":ObjectId(args.db_id), "run.start_time":{"$exists": True}, \
             "outdir":{"$exists": True}})
            #Check for analysis status updates
            check_completion_status(results, args.db_id, args.outdir)
            if results.count() == 1:
                logger.info("Re-running the analysis")
                try:
                    if args.dry_run:
                        dry_run_skip()
                    db.update({"_id": ObjectId(args.db_id)},
                        {"$set":
                            {"run.status": "RESTART"
                        }})
                    db.update({"_id": ObjectId(args.db_id)},
                        {"$unset":
                            {"run.end_time": ""
                        }})
                    db.update({"_id": ObjectId(args.db_id)},
                            {"$inc":{"run.num_restarts": 1}
                        })
                except pymongo.errors.OperationFailure:
                    logger.fatal("mongoDB OperationFailure")
                    sys.exit(1)
    elif args.mode == "check":
        logger.info("Checking snakemake logs for completion time and status")
        #Check if analysis has been started/restarted
        results = db.find({"_id":ObjectId(args.db_id), "run.status":{"$exists": True}})
        if results.count() != 1:
            logger.info("Analysis not yet started")
            sys.exit(0)
        #Check for analysis status updates
        check_completion_status(results, args.db_id, args.outdir)
        snake_logs = os.path.join(args.outdir + "/logs/snakemake.log")
        if os.path.exists(snake_logs):
            with open(snake_logs) as f:
                last_line = list(f)[-1]
                end_time_str = last_line.split("]")[0].replace("[", "")
                end_time = datetime.strptime(end_time_str, '%a %b %d %H:%M:%S %Y').isoformat(). \
                replace(":", "-")
                if "100%" in last_line:
                    try:
                        if args.dry_run:
                            dry_run_skip()
                        db.update({"_id": ObjectId(args.db_id)},
                            {"$set":
                                {"run.status": "SUCCESS",
                                "run.end_time": end_time
                            }})
                    except pymongo.errors.OperationFailure:
                        logger.fatal("mongoDB OperationFailure")
                        sys.exit(1)
                elif "Exiting" in last_line:
                    try:
                        if args.dry_run:
                            dry_run_skip()
                        db.update({"_id": ObjectId(args.db_id)},
                            {"$set":
                                {"run.status": "FAILED",
                                "run.end_time": end_time
                            }})
                        subject = "Analysis under {}".format(args.outdir)
                        body = subject + " FAILED"
                        send_mail(subject, body, mail_to)
                    except pymongo.errors.OperationFailure:
                        logger.fatal("mongoDB OperationFailure")
                        sys.exit(1)
                else:
                    logger.info("Analysis is not yet completed under %s", args.outdir)
        else:
            logger.critical("snake_logs does not exists")
    else:
        raise ValueError(args.mode)
    # close the connection to MongoDB
    connection.close()

if __name__ == "__main__":
    logger.info("MongoDB status update starting")
    main()
    logger.info("Successful program exit")
