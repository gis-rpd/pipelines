#!/usr/bin/env python3
"""MongoDB status updates for the bcl2fastq pipeline
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

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from utils import generate_timestamp
from pipelines import get_site
from pipelines import is_production_user
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
    parser.add_argument('-r', "--runid",
                        help="Run ID plus flowcell ID", required=True,)
    parser.add_argument('-s', "--status",
                        help="Analysis status", required=True,
                        choices=['STARTED', 'SUCCESS', 'FAILED', 'SEQRUNFAILED', 'NON-BCL'])
    parser.add_argument('-a', "--analysis-id",
                        help="Analysis id", required=True)
    parser.add_argument('-o', "--out",
                        help="Analysis output directory")
    parser.add_argument('-t', "--test-server", action='store_true')
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

    if not is_production_user():
        logger.warning("Not a production user. Skipping MongoDB update")
        sys.exit(1)
    user_name = "userrig"
            
    run_number = args.runid
    connection = mongodb_conn(args.test_server)
    if connection is None:
        sys.exit(1)
    logger.info("Database connection established")
    db = connection.gisds.runcomplete
    logger.debug("DB %s", db)
    logger.info("Status for %s is %s", run_number, args.status)
    if args.status in ["STARTED", "SEQRUNFAILED"]:
        try:
            if not args.dry_run:
                res = db.update_one({"run": run_number},
                                    {"$push":
                                     {"analysis": {
                                         "analysis_id" : args.analysis_id,
                                         "user_name" : user_name,
                                         "out_dir" : args.out,
                                         "Status" :  args.status,
                                     }}})
                assert res.modified_count == 1, (
                    "Modified {} documents instead of 1".format(res.modified_count))
        except (pymongo.errors.OperationFailure, AssertionError) as e:
            logger.fatal("MongoDB update failure while setting run %s analysis_id %s to %s",
                         run_number, args.analysis_id, args.status)
            sys.exit(1)

    elif args.status in ["SUCCESS", "FAILED"]:
        end_time = generate_timestamp()
        logger.info("Setting timestamp to %s", end_time)
        try:
            if not args.dry_run:
                res = db.update_one({"run": run_number, 'analysis.analysis_id' : args.analysis_id},
                                    {"$set":
                                     {"analysis.$": {
                                         "analysis_id" : args.analysis_id,
                                         "end_time" : end_time,
                                         "user_name" : user_name,
                                         "out_dir" : args.out,
                                         "Status" :  args.status,
                                     }}})
                assert res.modified_count == 1, (
                    "Modified {} documents instead of 1".format(res.modified_count))
        except (pymongo.errors.OperationFailure, AssertionError) as e:
            logger.fatal("MongoDB update failure while setting run %s analysis_id %s to %s",
                         run_number, args.analysis_id, args.status)
            sys.exit(1)

    else:
        raise ValueError(args.status)

    # close the connection to MongoDB
    connection.close()


if __name__ == "__main__":
    logger.info("MongoDB status update starting")
    main()
    logger.info("Successful program exit")
