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
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)


def usage():
    """print usage info"""
    sys.stderr.write("useage: {} [-1]".format(
        os.path.basename(sys.argv[0])))

    
def mongodb_conn(test_server=False):
    """start connection to server and return conncetion"""
    if test_server:
        logger.warning("Using test server connection")
        conn_str = "qlap33:27017"
        
    else:
        logger.warning("Using Productionserver connection")
        conn_str = "qldb01.gis.a-star.edu.sg:27017,qlap37.gis.a-star.edu.sg:27017,qlap38.gis.a-star.edu.sg:27017,qlap39.gis.a-star.edu.sg:27017"

    try:
        connection = pymongo.MongoClient(conn_str)
    except pymongo.errors.ConnectionFailure:
        logger.fatal("Could not connect to the mongoDB server")
        sys.exit(1)
    return connection
    
        
def main():
    """main function"""        
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-r', "--runid",
                        help="Run ID plus flowcell ID",required=True,)
    parser.add_argument('-s', "--status",
                        help="Analysis status",required=True,
                        choices=['START', 'SUCCESS', 'FAILED', 'SEQRUNFAILED'])
    parser.add_argument('-id', "--id",
                        help="Analysis id",required=True)                   
    parser.add_argument('-o', "--out",
                        help="Analysis output directory") 
    parser.add_argument('-t', "--test_server", action='store_true')
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
        logger.warn("Not a production user. Skipping MongoDb update")
        sys.exit(0)

        
    run_number = args.runid
    connection = mongodb_conn(args.test_server)
    logger.info("Database connection established")
    db = connection.gisds.runcomplete
    logger.debug("DB {}".format(db))
    
    start_time = args.id    
    logger.info("Database connection established {}".format(run_number))
    if args.status == "START":
        logger.info("Status updte is START {}".format(start_time))
        try:
            db.update({"run": run_number},
            {"$push": 
                {"analysis": {
                    "analysis_id" : start_time,
                    "startTime" : start_time,
                    "userName" : user_name,
                    "out_dir" : args.out
            }}})
                
        except pymongo.errors.OperationFailure:
            logger.fatal("mongoDB OperationFailure")
            sys.exit(0)
    elif args.status == "SEQRUNFAILED":
        logger.info("Status updte is START {}".format(start_time))
        try:
            db.update({"run": run_number},
            {"$push": 
                {"analysis": {
                    "analysis_id" : start_time,
                    "startTime" : start_time,
                    "userName" : user_name,
                    "out_dir" : args.out,
                    "Status" :  "SEQRUNFAILED",
            }}})
                
        except pymongo.errors.OperationFailure:
            logger.fatal("mongoDB OperationFailure")
            sys.exit(0)
    elif args.status == "SUCCESS":
        end_time = generate_timestamp()
        logger.info("Status updte is END and timestamp {}".format(end_time))
        try:
            db.update({"run": run_number, 'analysis.analysis_id' : start_time},
                {"$set": 
                    {"analysis.$": {
                        "analysis_id" : start_time,
                        "startTime" : start_time,
                        "EndTime" : end_time,
                        "userName" : user_name,
                        "Status" :  "SUCCESS",
                        "out_dir" : args.out
            }}})
        except pymongo.errors.OperationFailure:
            logger.fatal("mongoDB OperationFailure")
            sys.exit(0)
        
    elif args.status == "FAILED":
        logger.info("Send FAILEURE message")
        end_time = generate_timestamp()
        logger.info("Status updte is FAILED and timestamp {}".format(end_time))
        print (end_time)
        try:
            db.update({"run": run_number, 'analysis.analysis_id' : start_time},
                {"$set": 
                    {"analysis.$": {
                        "analysis_id" : start_time,
                        "startTime" : start_time,
                        "EndTime" : end_time,
                        "userName" : user_name,
                        "Status" :  "FAILED",
                        "out_dir" : args.out
            }}})
        except pymongo.errors.OperationFailure:
            logger.fatal("mongoDB OperationFailure")
            sys.exit(0)
        
    # close the connection to MongoDB
    connection.close()
    
    

if __name__ == "__main__":
    logger.info("MongoDB status update starting")
    main()
    logger.info("Successful program exit")
