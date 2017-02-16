#!/usr/bin/env python3
"""MongoDB status updates for the downstream pipeline
"""

# standard library imports
import logging
import sys
import os
import argparse
import pprint
import datetime

#--- third party imports
#
import pymongo
from bson.objectid import ObjectId
import dateutil

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from pipelines import PipelineHandler
from pipelines import generate_timestamp
from pipelines import is_production_user
from pipelines import snakemake_log_status
from mongodb import mongodb_conn


__author__ = "Lavanya Veeravalli"
__email__ = "veeravallil@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# global logger
LOGGER = logging.getLogger(__name__)
HANDLER = logging.StreamHandler()
HANDLER.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
LOGGER.addHandler(HANDLER)


THRESHOLD_H_SINCE_LAST_TIMESTAMP = 24
THRESHOLD_H_SINCE_START = 72


def list_job(db, db_id, dry_run):
    """Just list entry for this db_id
    """

    if dry_run:# only for compat with other function
        return

    if db_id == "STARTED":
        cursor = db.find({"run.status": "STARTED"})
        for r in cursor:
            pprint.pprint(r)
    else:
        cursor = db.find_one({"_id": ObjectId(db_id)})
        assert cursor, "No objects found with db-id {}".format(db_id)
        pprint.pprint(cursor)


def check_completion(db, db_id, dry_run):
    """Update values for already started job based on log file in outdir
    """

    if db_id == 'STARTED':
        cursor = db.find({"run.status": "STARTED"})
        LOGGER.info("Will check %s started jobs", cursor.count())
    else:
        cursor = db.find_one({"_id": ObjectId(db_id)})
        assert cursor, "No object found with db-id {}".format(db_id)

    for record in cursor:
        db_id = record['_id']# in case we used 'STARTED'
        if not record.get('run'):
            LOGGER.critical("Looks like job %s was never started (run entry missing)", db_id)
            continue

        old_status = record['run'].get('status')
        start_time = record['run'].get('start_time')
        if not old_status or not start_time:
            LOGGER.critical("Job start for %s was not logged properly (status or start_time not set)", db_id)
            continue
        elif old_status != "STARTED":
            LOGGER.critical("Status for job %s already set to %s", db_id, old_status)
            sys.exit(1)

        outdir = record.get('outdir')
        assert outdir, ("outdir missing for started job %s", db_id)

        if dry_run:
            LOGGER.info("Skipping due to dryrun option")
            return

        snakelog = os.path.join(outdir, PipelineHandler.MASTERLOG)
        LOGGER.info("Checking snakemake log %s for status of job %s", snakelog, db_id)
        if not os.path.exists(snakelog):
            LOGGER.critical("Expected snakemake log file %s for job %s doesn't exist.", snakelog, db_id)
            continue

        status, end_time = snakemake_log_status(snakelog)

        LOGGER.info("Job %s has status %s (end time %s)",
                    db_id, status, end_time)
        if status == "SUCCESS":
            assert end_time
            db.update({"_id": ObjectId(db_id)},
                      {"$set": {"run.status": "SUCCESS",
                                "run.end_time": end_time}})
        elif status == "ERROR":
            assert end_time
            db.update({"_id": ObjectId(db_id)},
                      {"$set": {"run.status": "FAILED",
                                "run.end_time": end_time}})
        else:
            if end_time:# without status end_time means last seen time in snakemake
                delta = datetime.now() - dateutil.parser.parse(end_time)
                diff_min, _diff_secs = divmod(delta.days * 86400 + delta.seconds, 60)
                diff_hours = diff_min/60.0
                if diff_hours > THRESHOLD_H_SINCE_LAST_TIMESTAMP:
                    LOGGER.critical("Last update for job id %s was seen %s hours ago", db_id, diff_hours)

            delta = datetime.now() - dateutil.parser.parse(start_time)
            diff_min, _diff_secs = divmod(delta.days * 86400 + delta.seconds, 60)
            diff_hours = diff_min/60.0
            if diff_hours > THRESHOLD_H_SINCE_START:
                LOGGER.critical("Job id %s was started %s hours ago", db_id, diff_hours)



def started_or_restarted(db, db_id, outdir, dry_run):
    """Update records for started or restarted analysis
    """

    cursor = db.find_one({"_id": ObjectId(db_id)})
    assert cursor, "No objects found with db-id {}".format(db_id)

    # determine if this is a start or a restart (or a mistake)
    if cursor.get('run') and cursor.get('outdir'):
        assert cursor['run']['start_time']
        assert cursor['run'].get('status') is not None
        mode = 'restart'
    elif cursor.get('run') is None and cursor.get('outdir') is None:
        mode = 'start'
    else:
        raise ValueError(db_id, cursor['run'], cursor['outdir'])

    LOGGER.info("Updating %sed job %s", mode, db_id)
    if dry_run:
        LOGGER.info("Skipping due to dryrun option")
        return

    if mode == 'start':
        start_time = generate_timestamp()
        res = db.update_one(
            {"_id": ObjectId(db_id)},
            {"$set": {"outdir": outdir,
                      "run": {"start_time" : start_time, "status" : "STARTED"}}})
        assert res.modified_count == 1, (
            "Modified {} documents instead of 1".format(res.modified_count))

    elif mode == 'restart':
        res = db.update_one({"_id": ObjectId(db_id)},
                            {"$set": {"run.status": "RESTART"}})
        assert res.modified_count == 1, (
            "Modified {} documents instead of 1".format(res.modified_count))

        res = db.update_one({"_id": ObjectId(db_id)},
                            {"$unset": {"run.end_time": ""}})
        assert res.modified_count == 1, (
            "Modified {} documents instead of 1".format(res.modified_count))

        res = db.update_one({"_id": ObjectId(db_id)},
                            {"$inc":{"run.num_restarts": 1}})
        assert res.modified_count == 1, (
            "Modified {} documents instead of 1".format(res.modified_count))

    else:
        raise ValueError(mode)


def main():
    """main function"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-d', "--db-id",
                        help="DB id (in check and list mode you can use 'STARTED' for all started jobs)", required=True,)
    parser.add_argument('-o', "--outdir",
                        help="out directory")
    parser.add_argument('-m', "--mode",
                        help="mode", required=True,
                        choices=['start', 'check', 'list'])
    parser.add_argument('-t', "--test-db", action='store_true',
                        help="Use test database")
    parser.add_argument('-n', "--dry-run", action='store_true',
                        help="Dry run")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Increase verbosity")
    parser.add_argument('-q', '--quiet', action='count', default=0,
                        help="Decrease verbosity")
    args = parser.parse_args()

    # Repeateable -v and -q for setting logging level.
    # See https://www.reddit.com/r/Python/comments/3nctlm/what_python_tools_should_i_be_using_on_every/
    LOGGER.setLevel(logging.WARN + 10*args.quiet - 10*args.verbose)

    if not is_production_user():
        LOGGER.warning("Not a production user. Skipping MongoDB update")
        sys.exit(1)

    connection = mongodb_conn(args.test_db)
    if connection is None:
        sys.exit(1)
    LOGGER.info("Database connection established")
    db = connection.gisds.pipeline_runs

    try:
        if args.mode == "start":
            if not args.outdir:
                LOGGER.fatal("Need output directory for mode %s", args.mode)
                sys.exit(1)
            started_or_restarted(db, args.db_id, args.outdir, args.dry_run)

        elif args.mode == "check":
            check_completion(db, args.db_id, args.dry_run)

        elif args.mode == "list":
            list_job(db, args.db_id, args.dry_run)

        else:
            raise ValueError(args.mode)

    except pymongo.errors.OperationFailure as e:
        LOGGER.fatal("MongoDB failure while updating db-id %s", args.db_id)
        sys.exit(1)

    connection.close()


if __name__ == "__main__":
    LOGGER.info("MongoDB status update starting")
    main()
    LOGGER.info("Successful program exit")
