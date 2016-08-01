"""library functions for pipelines
"""

#--- standard library imports
#
import logging

#--- third-party imports
#
import pymongo

#--- project specific imports
#
from pipelines import get_site
from services import mongo_conns


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"



# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)


def mongodb_conn(use_test_server=False):
    """Return connection to MongoDB server"""
    site = get_site()
    assert site in mongo_conns
    if use_test_server:
        logger.info("Using test MongoDB server")
        constr = mongo_conns[site]['test']
    else:
        logger.info("Using production MongoDB server")
        constr = mongo_conns[site]['production']

    try:
        connection = pymongo.MongoClient(constr)
    except pymongo.errors.ConnectionFailure:
        logger.fatal("Could not connect to the MongoDB server")
        return None
    logger.debug("Database connection established")
    return connection

