#!/usr/bin/env python3
"""MongoDB_status from Bcl2fastq pipeline
"""
# standard library imports
import logging
import sys
import os
import argparse
import getpass

# third party imports
import pymongo

#--- project specific imports
#
from pipelines import generate_timestamp

__author__ = "Lavanya Veeravalli"
__email__ = "veeravallil@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# global logger
# http://docs.python.org/library/logging.html
LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] %(levelname)s %(filename)s: %(message)s')


def usage():
    """print usage info"""
    sys.stderr.write("useage: {} [-1]".format(
        os.path.basename(sys.argv[0])))

    
def mongodb_conn(test_server=False):
    """start connection to server and return conncetion"""
    if test_server:
        LOG.warning("Using test server connection")
        conn_str = "qlap33:27017"
        
    else:
        LOG.warning("Using Productionserver connection")
        conn_str = "qldb01.gis.a-star.edu.sg:27017,qlap37.gis.a-star.edu.sg:27017,qlap38.gis.a-star.edu.sg:27017,qlap39.gis.a-star.edu.sg:27017"

    try:
        connection = pymongo.MongoClient(conn_str)
    except pymongo.errors.ConnectionFailure:
        LOG.fatal("Could not connect to the mongoDB server")
        sys.exit(1)
    return connection
    
        
def main():
    """main function"""        
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-r', "--runid",
                        help="Run ID plus flowcell ID",required=True,)
    parser.add_argument('-s', "--status",
                        help="Analysis status",required=True,
                        choices=['START', 'SUCCESS', 'FAILED'])
    parser.add_argument('-id', "--id",
                        help="Analysis id",required=True)                   
    #parser.add_argument('-n', "--dry-run", action='store_true')
    parser.add_argument('-t', "--test_server", action='store_true')
    args = parser.parse_args()

    
    user_name = getpass.getuser()
    if user_name != "userrig":
        LOG.warn("Not a production user. Skipping MongoDb update")
        sys.exit(0)

        
    run_number = args.runid
    connection = mongodb_conn(args.test_server)
    LOG.info("Database connection established")
    db = connection.gisds.runcomplete
    LOG.debug("DB {}".format(db))
    
    start_time = args.id    
    LOG.info("Database connection established {}".format(run_number))
    if args.status == "START":
        LOG.info("Status updte is START {}".format(start_time))
        try:
            db.update({"run": run_number},
            {"$push": 
                {"analysis": {
                    "analysis_id" : start_time,
                    "startTime" : start_time,
                    "userName" : user_name
            }}})
                
        except pymongo.errors.OperationFailure:
            LOG.fatal("mongoDB OperationFailure")
            sys.exit(0)
    elif args.status == "SUCCESS":
        end_time = generate_timestamp()
        LOG.info("Status updte is END and timestamp {}".format(end_time))
        try:
            db.update({"run": run_number, 'analysis.analysis_id' : start_time},
                {"$set": 
                    {"analysis.$": {
                        "analysis_id" : start_time,
                        "startTime" : start_time,
                        "EndTimes" : end_time,
                        "userName" : user_name,
                        "Status" :  "SUCCESS"
            }}})
        except pymongo.errors.OperationFailure:
            LOG.fatal("mongoDB OperationFailure")
            sys.exit(0)
        
    elif args.status == "FAILED":
        LOG.info("Send FAILEURE message")
        end_time = generate_timestamp()
        LOG.info("Status updte is FAILED and timestamp {}".format(end_time))
        print (end_time)
        try:
            db.update({"run": run_number, 'analysis.analysis_id' : start_time},
                {"$set": 
                    {"analysis.$": {
                        "analysis_id" : start_time,
                        "startTime" : start_time,
                        "Ended" : end_time,
                        "userName" : user_name,
                        "Status" :  "FAILED"
            }}})
        except pymongo.errors.OperationFailure:
            LOG.fatal("mongoDB OperationFailure")
            sys.exit(0)
        
    # close the connection to MongoDB
    connection.close()
    
    

if __name__ == "__main__":
    LOG.info("MongoDB status update starting")
    main()
    LOG.info("Successful program exit")
