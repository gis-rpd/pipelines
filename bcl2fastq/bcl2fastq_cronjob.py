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
logging.basicConfig(level=logging.INFO,
                    format='%(levelname)s [%(asctime)s]: %(message)s')


def generate_timestamp(days=14):
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
    parser.add_argument('-1', "--break-after-first", action='store_true')
    parser.add_argument('-n', "--dry-run", action='store_true')
    parser.add_argument('-t', "--test-server", action='store_true')
    args = parser.parse_args()
    

    connection = mongodb_conn(args.test_server)
    db = connection.gisds.runcomplete
    LOG.info("Database connection established")
    #DB Query for Jobs that are yet to be analysed in the epoch window

    # FIXME each run object ideally can have 0 or multiple analysis
    # objects this scripts only kickstarts if no analysis objects.
    # (later: if --force-failed is given try again for those with
    # exactly one failed. send email for two fail) Analysis object:
    # initiated:timestamp, ended:timestamp,
    # status:"completed"|"troubleshooting"
    epoch_present, epoch_back = generate_timestamp()
    results = db.find({"analysis": { "$exists" : 0 },
                       "timestamp": {"$gt": epoch_back, "$lt": epoch_present}})

    # display documents from collection
    #LOG.info("Looping over {} results".format(len(results)))
    #LOG.debug(epoch_present, epoch_back)
    for record in results:
        run_number = record['run']
        if args.dry_run:
            LOG.critical("Should call bcl_wrapper.py for {}".format(run_number))
        else:
            raise NotImplementedError("Calling bcl2fastq wrapper not implemented yet")
        
        #Update the analysis field
        # FIXME see above
        #db.update({"run": run_number},{"$set": {"analysis": {
        #    "_id.uid": 0,
        #    "Initiated" : epoch_present,
        #    "Ended" : 00000,
        #    "Status" : "check"
        #}}})
        if args.break_after_first:
            LOG.warn("Stopping after first sequencing run")
            break

    # close the connection to MongoDB
    connection.close()

    
if __name__ == "__main__":
    LOG.info("Cronjob starting")
    main()
    LOG.info("Successful program exit")

    
