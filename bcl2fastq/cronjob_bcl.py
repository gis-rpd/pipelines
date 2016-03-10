#!/usr/bin/env python3
import logging 
import time
from datetime import datetime, timedelta
import sys
import json

import pymongo


# FIXME run pylint later

ONE_RUN_AT_A_TIME = True

# global logger
# http://docs.python.org/library/logging.html
LOG = logging.getLogger("")
logging.basicConfig(level=logging.INFO,
                    format='%(levelname)s [%(asctime)s]: %(message)s')
                    

def generate_timestamp(days=15):
    """returns tuple representing epoch window (int:present, int:past)"""
    date_time = time.strftime('%Y-%m-%d %H:%M:%S')
    #print (date_time)
    pattern = '%Y-%m-%d %H:%M:%S'
    epoch_present = int(time.mktime(time.strptime(date_time, pattern)))*1000
    d = datetime.now() - timedelta(days=days)
    f = d.strftime("%Y-%m-%d %H:%m:%S")
    epoch_back = int(time.mktime(time.strptime(f, pattern)))*1000
    return (epoch_present, epoch_back)
                    
def mongodb_conn(use_test_server=True):
    if use_test_server:
        conn_str = "qlap33:27017"
    else:
        conn_str = "qldb01:27017,qlap37:27017,qlap38:27017,qlap39:27017"
        
    try:
        connection = pymongo.MongoClient(conn_str)
    except pymongo.errors.ConnectionFailure:
        LOG.fatal("Could not connect to the mongoDB server")
        sys.exit(1)
    return connection
    
def main():
    epoch_present, epoch_back = generate_timestamp()
    
    print (epoch_present)
    print (epoch_back)
    
    connection = mongodb_conn()
    db = connection.gisds.runcomplete
    #DB Query for Jobs that are yet to be analysed in the epoch window
    
    # FIXME each run object ideally can have 0 or multiple analysis objects
    # this scripts only kickstarts if no analysis objects
    # (later: if --force-failed is given try again for those with exactly one failed. send email for two fail)
    # Analysis object: initiated:timestamp, ended:timestamp, status:"completed"|"troubleshooting" 
    results = db.find({"analysis": { "$exists" : 0 }, "timestamp": {"$gt": epoch_back , "$lt": epoch_present}})
    #LOG.info("Looping over {} results".format(len(results)))
  
    
    # display documents from collection
    for record in results:
        print(record)
        runNumber = record['run']
        # Call the Bcl wrapper for the run
        
        ###LOG.critical("FIXME call bcl_wrapper.py" + runNumber)
        
        #Update the analysis field
        # FIXME see above
        #db.update({"run": runNumber},{"$set": {"analysis": {
        #    "_id.uid": 0,
        #    "Initiated" : epoch_present, 
        #    "Ended" : 00000, 
        #    "Status" : "check" 
        #}}})
        if ONE_RUN_AT_A_TIME:
            LOG.info("Breaking after first run")
            break
    LOG.info("close the DB connection")
    # close the connection to MongoDB
    connection.close()
     
if __name__ == "__main__":
    main()
    LOG.info("Successful program exit")

    