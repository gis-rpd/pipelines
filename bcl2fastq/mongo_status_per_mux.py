#!/usr/bin/env python3
"""MUX specific MongoDB status updates
"""
# standard library imports
import logging
import sys
import argparse
import getpass

#--- third party imports
# WARN: need in conda root and snakemake env
import pymongo

#--- project specific imports
#
from mongo_status import mongodb_conn


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
    parser.add_argument('-a', "--analysis-id",
                        help="Analysis id / start time", required=True)
    parser.add_argument('-i', "--mux-id",
                        help="mux-id", required=True)
    parser.add_argument('-d', "--mux-dir",
                        help="mux-dir", required=True)
    parser.add_argument('-s', "--mux-status",
                        help="Analysis status", required=True,
                        choices=['SUCCESS', 'FAILED'])

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

    run_number = args.runid.rstrip()
    connection = mongodb_conn(args.test_server)
    if connection is None:
        sys.exit(1)
    logger.info("Database connection established")
    db = connection.gisds.runcomplete
    if args.mux_status == "SUCCESS":
        try:
            if not args.dry_run:
                db.update({"run": run_number, 'analysis.analysis_id' : args.analysis_id},
                          {
                              "$push": {
                                  "analysis.$.per_mux_status":  {
                                      "mux_id" : args.mux_id,
                                      "mux_dir" : args.mux_dir,
                                      "Status" : args.mux_status,
                                      "StatsSubmission" : "TODO",
                                      "ArchiveSubmission" : "TODO",
                                      "DownstreamSubmission" : "TODO",
                                      "email_sent" : False,

                                  }}})
        except pymongo.errors.OperationFailure:
            logger.fatal("mongoDB OperationFailure")
            sys.exit(0)
    elif args.mux_status == "FAILED":
        try:
            if not args.dry_run:
                db.update({"run": run_number, 'analysis.analysis_id' : args.analysis_id},
                          {
                              "$push": {
                                  "analysis.$.per_mux_status":  {
                                      "mux_id" : args.mux_id,
                                      "mux_dir" : args.mux_dir,
                                      "Status" : args.mux_status,
                                      "email_sent" : False,
                                  }}})
        except pymongo.errors.OperationFailure:
            logger.fatal("mongoDB OperationFailure")
            sys.exit(0)
    else:
        raise ValueError(args.status)
     # close the connection to MongoDB
    connection.close()

if __name__ == "__main__":
    logger.info("MongoDB status update starting")
    main()
    logger.info("Successful program exit")
