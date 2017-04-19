#!/usr/bin/env python3
"""Basically a pipeline starter and also frontend to logger

see https://bitbucket.org/liewjx/rpd
"""

#--- standard library imports
#
import logging
import sys
import os
import argparse
#import pprint
import glob

#--- third party imports
#
#import yaml

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from mongodb import mongodb_conn
from pipelines import is_production_user
from pipelines import generate_window
from pipelines import get_downstream_outdir
from pipelines import generate_timestamp
from pipelines import timestamp_from_string


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2017 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# global logger
LOGGER = logging.getLogger(__name__)
HANDLER = logging.StreamHandler()
HANDLER.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
LOGGER.addHandler(HANDLER)


class StarterFlag(object):
    """Flag files indicating analysis start
    """


    pattern = "STARTER_FLAG.{timestamp}"


    def __init__(self, filename=None):
        """
        """

        if filename:
            self.read(filename)
        else:
            self.filename = None
            self.timestamp = None
            self.dbid = None


    def _timestamp_from_filename(self, filename):
        """Get timestamp from filename
        """

        tstr = os.path.basename(filename).replace(
            self.pattern.format(timestamp=""), "")
        return timestamp_from_string(tstr)


    def read(self, filename):
        """Read flag file (timestamp and dbid)
        """
        self.filename = filename
        self.timestamp = self._timestamp_from_filename(self.filename)
        with open(self.filename, 'r') as fh:
            self.dbid = fh.read().decode()


    def write(self, dirname, dbid, timestamp=None):
        """Write starter flag file
        """

        if not timestamp:
            timestamp = generate_timestamp()
        self.timestamp = timestamp
        self.dbid = dbid
        self.filename = os.path.join(dirname, self.pattern.format(timestamp=self.timestamp))

        assert not os.path.exists(self.filename), (
            "StartFlag {} already exists".format(self.filename))
        with open(self.filename, 'w') as fh:
            fh.write(dbid)


def list_starterflags(path):
    """
    """
    return glob.glob(os.path.join(
        path, StarterFlag.pattern.format(timestamp="*")))


def main():
    """main function
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-n', "--dry-run", action='store_true',
                        help="Don't run anything")
    parser.add_argument('-s', "--site",
                        help="site information")
    parser.add_argument('-t', "--testing", action='store_true',
                        help="Use MongoDB test-server. Don't do anything")
    default = 14
    parser.add_argument('-w', '--win', type=int, default=default,
                        help="Number of days to look back (default {})".format(default))
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Increase verbosity")
    parser.add_argument('-q', '--quiet', action='count', default=0,
                        help="Decrease verbosity")
    args = parser.parse_args()

    # Repeateable -v and -q for setting logging level.
    # See https://www.reddit.com/r/Python/comments/3nctlm/what_python_tools_should_i_be_using_on_every
    LOGGER.setLevel(logging.WARN + 10*args.quiet - 10*args.verbose)

    if not is_production_user():
        LOGGER.warning("Not a production user. Exiting")
        sys.exit(1)

    connection = mongodb_conn(args.testing)
    if connection is None:
        sys.exit(1)
    LOGGER.info("Database connection established")
    db = connection.gisds.pipeline_runs

    epoch_now, epoch_then = generate_window(args.win)
    cursor = db.find({"ctime": {"$gt": epoch_then, "$lt": epoch_now}})
    LOGGER.info("Looping through {} jobs".format(cursor.count()))
    for job in cursor:

        #objid = ObjectId(record['_id'])
        objid = job['_id']


        try:
            # only set here to avoid code duplication below
            out_dir = job['execution']['out_dir']
        except KeyError:
            out_dir = None

        # a new analysis to start
        if not job.get('execution'):
            LOGGER.info('Job {} to be started'.format(objid))

            # determine out_dir and set in DB
            out_dir = get_downstream_outdir(
                job['requestor'], job['pipeline_name'], job['pipeline_version'])
            res = db.update_one(
                {"_id": objid},
                {"$set": {"execution.out_dir": out_dir}})
            assert res.modified_count == 1, (
                "Modified {} documents instead of 1".format(res.modified_count))

            # Note, since execution (key) exists, accidental double
            # starts are prevented even before start time etc is
            # logged via flagfiles.  No active logging here so that
            # flag files logging just works.

            # FIXME Start new run by calling the resp. wrapper with resp. parameters
            raise(NotImplementedError("Start new run for {}".format(objid)))

        elif list_starterflags(out_dir):# if out_dir is None, then something's wrong
            LOGGER.info('Job {} in {} started but not yet logged as such in DB'.format(
                objid, out_dir))

            matches = list_starterflags(out_dir)
            assert len(matches) == 1, (
                "Got several starter flags in {}".format(out_dir))
            sflag = StarterFlag(matches[0])
            assert sflag.dbid == objid

            # FIXME call logger
            raise(NotImplementedError(
                "Run downstream_logger.py in `start` mode with start time {} and db-id {}".format(
                    sflag.timestamp, sflag.dbid)))

            os.unlink(sflag.filename)

        elif job['execution'].get('status') in ['STARTED', 'RESTARTED']:
            LOGGER.info('Job {} in {} set as re|started so checking on completion'.format(
                objid, out_dir))
            raise(NotImplementedError(
                "Run downstream_logger.py in `check_completion` mode db-id {}".format(objid)))

        else:
            # job complete
            LOGGER.debug('Job {} in {} should be completed'.format(objid, out_dir))


if __name__ == "__main__":
    main()
