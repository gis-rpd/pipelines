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
import pymongo

# project specificy imports
# /


__author__ = "Lavanya Veeravalli"
__email__ = "veeravallil@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# global logger
# http://docs.python.org/library/logging.html
LOG = logging.getLogger("")



def generate_window(days=14):
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
        LOG.warning("Using test server connection")
        conn_str = "qlap33:27017"
    else:
        conn_str = "qldb01:27017,qlap37:27017,qlap38:27017,qlap39:27017"

    try:
        connection = pymongo.MongoClient(conn_str)
    except pymongo.errors.ConnectionFailure:
        LOG.fatal("Could not connect to the mongoDB server")
        sys.exit(1)
    return connection


def usage():
    """print usage info"""
    sys.stderr.write("useage: {} [-1]".format(
        os.path.basename(sys.argv[0])))


def main():
    """main function"""


    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-1', "--break-after-first", action='store_true', help="Only process first run returned")
    parser.add_argument('-n', "--dry-run", action='store_true', help="Don't run anything")
    parser.add_argument('-t', "--testing", action='store_true', help="Use mongoDB test-server here and in wrapper and disable SRA upload in wrapper")
    parser.add_argument('-e', "--wrapper-args", help="Extra arguments for bcl2fastq wrapper (prefix leading dashes with X)")
    parser.add_argument('-q', '--quiet', action='store_true', help="Be quiet (only print warnings)")
    args = parser.parse_args()

    # FIXME broken    
    if args.quiet:
        logging.basicConfig(level=logging.WARN,
            format='%(levelname)s [%(asctime)s]: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO,
            format='%(levelname)s [%(asctime)s]: %(message)s')
            
    connection = mongodb_conn(args.testing)
    db = connection.gisds.runcomplete
    LOG.info("Database connection established")
    #DB Query for Jobs that are yet to be analysed in the epoch window

    # FIXME each run object ideally can have 0 or multiple analysis
    # objects this scripts only kickstarts if no analysis objects.
    # (later: if --force-failed is given try again for those with
    # exactly one failed. send email for two fail) Analysis object:
    # initiated:timestamp, ended:timestamp,
    # status:"completed"|"troubleshooting"
    epoch_present, epoch_back = generate_window()
    results = db.find({"analysis": { "$exists" : 0 },
                       "timestamp": {"$gt": epoch_back, "$lt": epoch_present}})

    bcl2fastq_wrapper = os.path.join(os.path.dirname(sys.argv[0]), "bcl2fastq.py")
    
    # display documents from collection
    #LOG.info("Looping over {} results".format(len(results)))
    #LOG.debug(epoch_present, epoch_back)
    for record in results:
        run_number = record['run']

        cmd = [bcl2fastq_wrapper, "-r", run_number]
        if args.testing:
            cmd.append("-t")
        if args.wrapper_args:
            cmd.extend([x.lstrip('X') for x in args.wrapper_args.split()])
        if args.dry_run:
            LOG.warn("Didn't run {}".format(' '.join(cmd))); continue            
        else:
            try:
                res = subprocess.check_output(cmd)
                LOG.info("bcl2fastq wrapper returned: {}".format(res.decode()))
            except subprocess.CalledProcessError:
                LOG.critical("The following failed: {}. Will keep going".format(' '.join(cmd)))
                
        if args.break_after_first:
            LOG.warn("Stopping after first sequencing run")
            break

    # close the connection to MongoDB
    connection.close()

    
if __name__ == "__main__":
    LOG.info("Cronjob starting")
    main()
    LOG.info("Successful program exit")

    