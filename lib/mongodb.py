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

# first level key must match output of get_site()
CONMAP = {
    'gis': {
        'test': "qlap33.gis.a-star.edu.sg:27017",
        'production': "qldb01.gis.a-star.edu.sg:27017,qlap37.gis.a-star.edu.sg:27017,qlap38.gis.a-star.edu.sg:27017,qlap39.gis.a-star.edu.sg:27017"
        },
    'nscc': {
        # using reverse proxy @LMN
        #'test': "192.168.190.1:27020",
        #'production': "192.168.190.1:27016,192.168.190.1:27017,192.168.190.1:27018,192.168.190.1:27019"
        'test': "qlap33.gis.a-star.edu.sg:27017",
        'production': "qldb01.gis.a-star.edu.sg:27017,qlap37.gis.a-star.edu.sg:27017,qlap38.gis.a-star.edu.sg:27017,qlap39.gis.a-star.edu.sg:27017"
        }
    }


def mongodb_conn(use_test_server=False):
    """Return connection to MongoDB server"""
    site = get_site()
    assert site in CONMAP
    if use_test_server:
        logger.info("Using test MongoDB server")
        constr = CONMAP[site]['test']
    else:
        logger.info("Using production MongoDB server")
        constr = CONMAP[site]['production']

    try:
        connection = pymongo.MongoClient(constr)
    except pymongo.errors.ConnectionFailure:
        logger.fatal("Could not connect to the MongoDB server")
        return None
    logger.debug("Database connection established")
    return connection

