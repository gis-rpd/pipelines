#!/usr/bin/env python3
""" Cronjob to archive novogene runs
"""
# standard library imports
import logging
import sys
import os
import argparse
import shutil

# project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from mongodb import mongodb_conn
from pipelines import generate_window
from pipelines import is_production_user
from pipelines import isoformat_to_epoch_time
from pipelines import get_machine_run_flowcell_id
from pipelines import is_devel_version
from pipelines import relative_epoch_time
from pipelines import send_mail
from pipelines import get_bcl_runfolder_for_runid
from config import site_cfg
from utils import generate_timestamp

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

def runs_from_db(db, days=75, win=34):
    """Get the runs from pipeline_run collections"""
    epoch_present, epoch_back = generate_window(win)
    results = db.find({"run" : {"$regex" : "^NG00"}, "raw-delete": {"$exists": False},
                       "timestamp": {"$gt": epoch_back, "$lt": epoch_present}})
    LOGGER.info("Found %d runs for last %s days", results.count(), win)
    for record in results:
        LOGGER.debug("record: %s", record)
        if not record.get('run'):
            LOGGER.critical("run is missing for DB-id %s", record['_id'])
            continue
        runid_and_flowcellid = (record['run'])
        results = db.find({"run": runid_and_flowcellid})
        if not 'analysis' in record:
            continue
        last_analysis = record['analysis'][-1]
        status = last_analysis.get("Status")
        end_time = last_analysis.get("end_time")
        if not status or not end_time:
            continue
        analysis_epoch_time = isoformat_to_epoch_time(end_time+"+08:00")
        epoch_time_now = isoformat_to_epoch_time(generate_timestamp()+"+08:00")
        rd = relative_epoch_time(epoch_time_now, analysis_epoch_time)
        relative_days = rd.months*30 + rd.days
        if status == 'SUCCESS' and relative_days > days:
            yield runid_and_flowcellid

def purge(db, runid_and_flowcellid, mail_to):
    """
    purging bcl data from /mnt/seq/novogene
    """
    rundir = get_bcl_runfolder_for_runid(runid_and_flowcellid)
    if not os.path.exists(rundir):
        LOGGER.critical("Run directory '%s' does not exist.\n", rundir)
        return
    # Sanity checks for Sequencing run
    assert os.path.exists(os.path.join(rundir, 'RunInfo.xml')), \
        "No RunInfo.xml found under {}".format(rundir)
    stat_info = os.stat(rundir)
    #Check if uid is novogene (925)
    assert stat_info.st_uid == 925, "The run {} does not belong to Novogene user".format(rundir)
    try:
        start_time = generate_timestamp()
        res = db.update_one({"run": runid_and_flowcellid}, \
                            {"$set": \
                                {"raw-delete": { \
                                    "start_time" : start_time, \
                                    "Status" :  "STARTED", \
                            }}})
        assert res.modified_count == 1, ("Modified {} documents instead of 1". \
            format(res.modified_count))
        #FIXME for production release
        #shutil.rmtree(rundir)
        end_time = generate_timestamp()
        res = db.update_one({"run": runid_and_flowcellid},
                            {"$set": {"raw-delete.Status": "SUCCESS", \
                                "raw-delete.end_time": end_time}})
        assert res.modified_count == 1, ("Modified {} documents instead of 1". \
            format(res.modified_count))
        subject = "bcl deletion: {}".format(runid_and_flowcellid)
        body = "Bcl deletion completed successfully from {}".format(rundir)
        send_mail(subject, body, toaddr=mail_to)
    except OSError:
        LOGGER.critical("Error happened while deleting '%s'", rundir)
        res = db.update_one({"run": runid_and_flowcellid}, \
                            {"$unset": {"raw-delete": ""}})
        assert res.modified_count == 1, ("Modified {} documents instead of 1". \
            format(res.modified_count))
        subject = "Error: bcl deletion {}".format(runid_and_flowcellid)
        body = "Error happened while deleting raw data under {}".format(rundir)
        send_mail(subject, body, toaddr=mail_to)

def main():
    """main function
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-1', "--break-after-first", action='store_true',
                        help="Only process first run returned")
    parser.add_argument('-n', "--dry-run", action='store_true',
                        help="Don't run anything")
    default = 34
    parser.add_argument('-w', '--win', type=int, default=default,
                        help="Number of days to look back (default {})".format(default))
    default = 75
    parser.add_argument('-d', '--days', type=int, default=default,
                        help="Bcl analysis not older than days(default {})".format(default))
    parser.add_argument('-t', "--testing", action='store_true',
                        help="Use MongoDB test-server here and when calling bcl2fastq wrapper (-t)")
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
    LOGGER.setLevel(logging.WARN + 10*args.quiet - 10*args.verbose)
    if not is_production_user():
        LOGGER.warning("Not a production user. Skipping archival steps")
        sys.exit(1)
    connection = mongodb_conn(args.testing)
    if connection is None:
        sys.exit(1)
    db = connection.gisds.runcomplete
    if is_devel_version() or args.testing:
        mail_to = 'veeravallil'# domain added in mail function
    else:
        mail_to = 'rpd'
    run_records = runs_from_db(db, args.days, args.win)
    for run in run_records:
        if args.dry_run:
            LOGGER.info("Skipping dryrun option %s", run)
            continue
        purge(db, run, mail_to)
        if args.break_after_first:
            LOGGER.info("Stopping after first sequencing run")
            break

if __name__ == "__main__":
    main()


