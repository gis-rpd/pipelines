#!/usr/bin/env python3
"""Cronjob for triggering bcl2fastq runs
"""


# standard library imports
import logging
import time
from datetime import datetime, timedelta
import sys
import os
import argparse
import subprocess

# third party imports
# WARN: need in conda root and snakemake env
import pymongo

# project specific imports
# /


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


def generate_window(days=7):
    """returns tuple representing epoch window (int:present, int:past)"""
    date_time = time.strftime('%Y-%m-%d %H:%M:%S')
    #print(date_time)
    pattern = '%Y-%m-%d %H:%M:%S'
    epoch_present = int(time.mktime(time.strptime(date_time, pattern)))*1000
    d = datetime.now() - timedelta(days=days)
    f = d.strftime("%Y-%m-%d %H:%m:%S")
    epoch_back = int(time.mktime(time.strptime(f, pattern)))*1000
    return (epoch_present, epoch_back)


def mongodb_conn(use_test_server=False):
    """start connection to server and return conncetion"""
    if use_test_server:
        logger.info("Using test MongoDB server")
        conn_str = "qlap33.gis.a-star.edu.sg:27017"
    else:
        logger.info("Using production MongoDB server")
        conn_str = "qldb01.gis.a-star.edu.sg:27017,qlap37.gis.a-star.edu.sg:27017,qlap38.gis.a-star.edu.sg:27017,qlap39.gis.a-star.edu.sg:27017"

    try:
        connection = pymongo.MongoClient(conn_str)
    except pymongo.errors.ConnectionFailure:
        logger.fatal("Could not connect to the MongoDB server")
        sys.exit(1)
    logger.debug("Database connection established")
    return connection


def usage():
    """print usage info"""
    sys.stderr.write("useage: {} [-1]".format(
        os.path.basename(sys.argv[0])))


def main():
    """main function"""


    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-1', "--break-after-first", action='store_true',
                        help="Only process first run returned")
    parser.add_argument('-n', "--dry-run", action='store_true',
                        help="Don't run anything")
    parser.add_argument('-t', "--testing", action='store_true',
                        help="Use MongoDB test-server here and when calling bcl2fastq wrapper (-t)")
    parser.add_argument('-e', "--wrapper-args", nargs="*",
                        help="Extra arguments for bcl2fastq wrapper (prefix leading dashes with X, e.g. X-n for -n)")
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
            
    connection = mongodb_conn(args.testing)
    db = connection.gisds.runcomplete
    #DB Query for Jobs that are yet to be analysed in the epoch window

    # FIXME each run object ideally can have 0 or multiple analysis
    # objects this scripts only kickstarts if no analysis objects are present.
    # (later: if --force-failed is given try again for those with
    # exactly one failed. send email for two fail) Analysis object:
    # initiated:timestamp, ended:timestamp,
    # status:"completed"|"troubleshooting"
    epoch_present, epoch_back = generate_window()
    results = db.find({"analysis": { "$exists" : 0 },
                       "timestamp": {"$gt": epoch_back, "$lt": epoch_present}})

    bcl2fastq_wrapper = os.path.join(os.path.dirname(sys.argv[0]), "bcl2fastq.py")
    
    # display documents from collection
    #logger.info("Looping over {} results".format(len(results)))
    #logger.debug(epoch_present, epoch_back)
    for record in results:
        run_number = record['run']

        cmd = [bcl2fastq_wrapper, "-r", run_number, "-v"]
        if args.testing:
            cmd.append("-t")
        if args.wrapper_args:
            cmd.extend([x.lstrip('X') for x in args.wrapper_args])
        if args.dry_run:
            logger.warn("Skipped following run: {}".format(' '.join(cmd)))
            continue            
        else:
            try:
                logger.info("Executing: {}".format(' '.join(cmd)))
                res = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
                if res:
                    logger.info("bcl2fastq wrapper returned: {}".format(res.decode()))
            except subprocess.CalledProcessError:
                logger.critical("The following failed: {}. Will keep going".format(' '.join(cmd)))
                
        if args.break_after_first:
            logger.warn("Stopping after first sequencing run")
            break

    # close the connection to MongoDB
    connection.close()
    logger.info("Successful program exit")

    
if __name__ == "__main__":
    main()

    
