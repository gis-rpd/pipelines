#!/usr/bin/env python3
""" Cronjob to archive novogene runs
"""
# standard library imports
import logging
import sys
import os
import argparse
import subprocess
import datetime
import shutil

#--- third party imports
#
import pymongo

# project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from mongodb import mongodb_conn
from pipelines import generate_window, is_production_user
from pipelines import isoformat_to_epoch_time, generate_timestamp
from pipelines import get_machine_run_flowcell_id, is_devel_version
from pipelines import relative_epoch_time, send_mail
from config import site_cfg

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

basedir = site_cfg['bcl2fastq_seqdir_base'].replace("userrig", "novogene")
archiveDir = basedir + "toDelete"

def runs_from_db(db, win=34):
    """Get the runs from pipeline_run collections"""
    epoch_present, epoch_back = generate_window(win)
    results = db.find({"run" : {"$regex" : "^NG00"}, "raw-delete": {"$exists": False},
                       "timestamp": {"$gt": epoch_back, "$lt": epoch_present}})
    logger.info("Found %d runs for last %s days", results.count(), win)
    for record in results:
        logger.debug("record: %s", record)
        if not record.get('run'):
            logger.critical("run is missing for DB-id %s", record['_id'])
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
        if status == 'SUCCESS' and rd.days > 21:
            yield runid_and_flowcellid

def run_folder_for_run_id(runid_and_flowcellid):
    """
    Get the run folder
    """
    machineid, runid, flowcellid = get_machine_run_flowcell_id(
        runid_and_flowcellid)
    rundir = "{}/{}/{}_{}".format(basedir, machineid, runid, flowcellid)
    return rundir

def purge(db, runid_and_flowcellid):
    """
    purging data from /mnt/seq/novogene
    """
    rundir = run_folder_for_run_id(runid_and_flowcellid)
    if not os.path.exists(rundir):
        logger.fatal("Run directory '%s' does not exist.\n", rundir)
        return
    start_time = generate_timestamp()
    res = db.update_one({"run": runid_and_flowcellid}, \
                        {"$set": \
                            {"raw-delete": { \
                                "start_time" : start_time, \
                                "Status" :  "STARTED", \
                        }}})
    assert res.modified_count == 1, ("Modified {} documents instead of 1". \
        format(res.modified_count))
    #FIXME shutil copyfile instead of MOVE to  dest directory.. for testing purpopse touch a file
    #Change form copy file to rmtree
    logger.info("Start archiving of %s", runid_and_flowcellid)
    src_dir = os.path.join(rundir, 'RTAComplete.txt')
    dest_dir = os.path.join(archiveDir, runid_and_flowcellid+"_RTAComplete.txt")
    try:
        shutil.copyfile(src_dir, dest_dir)
        end_time = generate_timestamp()
        res = db.update_one({"run": runid_and_flowcellid},
                            {"$set": {"raw-delete.Status": "SUCCESS", \
                                "raw-delete.end_time": end_time}})
        assert res.modified_count == 1, ("Modified {} documents instead of 1". \
            format(res.modified_count))
    except EnvironmentError:
        logger.CRITICAL("Error happened while copying")
        res = db.update_one({"run": runid_and_flowcellid}, \
                            {"$unset": {"raw-delete": ""}})
        assert res.modified_count == 1, ("Modified {} documents instead of 1". \
            format(res.modified_count))
        subject = "Moving of {} to {} failed".format(rundir, dest_dir)
        body = subject
        send_mail(subject, body, toaddr=mail_to, ccaddr=None)

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
    logger.setLevel(logging.WARN + 10*args.quiet - 10*args.verbose)
    if not is_production_user():
        logger.warning("Not a production user. Skipping MongoDB update")
        sys.exit(1)
    connection = mongodb_conn(args.testing)
    if connection is None:
        sys.exit(1)
    db = connection.gisds.runcomplete
    if is_devel_version() or args.testing:
        mail_to = 'veeravallil'# domain added in mail function
    else:
        mail_to = 'rpd'
    run_records = runs_from_db(db, args.win)
    body = ""
    for run in run_records:
        if args.dry_run:
            logger.info("Skipping dryrun option %s", run)
            body += "Analysis for {} has been completed 3 week ago. Please move or delete" \
                .format(run)
            body += "\n"
            continue
        try:
            purge(db, run)
        except pymongo.errors.OperationFailure as e:
            logger.fatal("MongoDB failure while updating db-id %s", args.db_id)
            sys.exit(1)
        if args.break_after_first:
            logger.info("Stopping after first sequencing run")
            break
        connection.close()
    if body:
        subject = "Novogene raw data deletion"
        print(body)
        send_mail(subject, body, toaddr=mail_to, ccaddr=None)

if __name__ == "__main__":
    main()


