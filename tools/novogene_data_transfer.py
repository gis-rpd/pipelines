#!/usr/bin/env python3
""" Cronjob to copy Novogene fastq data from GIS to NSCC
"""
# standard library imports
import logging
import sys
import os
import argparse
import subprocess

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
from pipelines import is_production_user, is_devel_version
from pipelines import generate_window
from config import novogene_conf

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

def runs_from_db(db, win=14):
    """Get the runs from pipeline_run collections"""
    epoch_present, epoch_back = generate_window(win)
    results = db.find({"run" : {"$regex" : "^NG00"},
                       "timestamp": {"$gt": epoch_back, "$lt": epoch_present}})
    logger.info("Found %d runs for last %s days", results.count(), win)
    for record in results:
        run_number = record['run']
        logger.debug("record: %s", record)
        if not record.get('analysis'):
            logger.critical("run is missing for DB-id %s", record['_id'])
            continue
        mux_list = {}
        for (analysis_count, analysis) in enumerate(record['analysis']):
            analysis_id = analysis['analysis_id']
            per_mux_status = analysis.get("per_mux_status", None)
            if per_mux_status is None:
                continue
            for (mux_count, mux_status) in enumerate(per_mux_status):
                # sanity checks against corrupted DB entries
                if mux_status is None or mux_status.get('mux_id') is None:
                    logger.warning("mux_status is None or incomplete for run %s analysis %s."
                                   " Requires fix in DB. Skipping entry for now.", \
                                    run_number, analysis_id)
                    continue
                if mux_status.get('Status', None) != "SUCCESS":
                    logger.info("MUX %s from %s is not SUCCESS. Skipping downstream analysis",
                                mux_status['mux_id'], run_number)
                    continue
                mux_id = mux_status['mux_id']
                out_dir = analysis['out_dir']
                downstream_id = "analysis.{}.per_mux_status.{}.DownstreamSubmission".format(
                    analysis_count, mux_count)
                if mux_status.get('Status') == "SUCCESS" and \
                    mux_status.get('DownstreamSubmission') == "TODO":
                    mongo_list = (run_number, downstream_id, analysis_id, out_dir)
                    if mux_id in mux_list:
                        #Send email the above message
                        logger.info("MUX %s has been analyzed more than 1 time succeessfully, \
                            send email", mux_id)
                        del mux_list[mux_id]
                    else:
                        mux_list[mux_id] = mongo_list
        if mux_list:
            yield mux_list

def update_mongodb(db, run_number, analysis_id, downstream_id, Status):
    """Update the status in the mongoDB runcomplete collection
    """
    try:
        db.update({"run": run_number, 'analysis.analysis_id' : analysis_id},
                  {"$set": {downstream_id: Status,}})
    except pymongo.errors.OperationFailure:
        logger.fatal("MongoDB OperationFailure")
        sys.exit(0)

def start_data_transfer(db, mux, info, site):
    """ Data transfer from source to destination
    """
    bcl_path = info[3]
    mux_fastq_path = os.path.join(bcl_path, "out", "Project_"+mux)
    bcl = os.path.basename(info[3])
    run_number = info[0]
    analysis_id = info[2]
    downstream_id = info[1]
    fastq_dest = os.path.join(novogene_conf['FASTQ_DEST'][site], mux, run_number, bcl)
    rsync_cmd = '/usr/bin/rsync -va %s %s' % (mux_fastq_path, fastq_dest)
    if not os.path.exists(fastq_dest):
        try:
            #Change the mongoDB status
            os.makedirs(fastq_dest)
            logger.info("data transfer started for %s from %s", mux, run_number)
            update_mongodb(db, run_number, analysis_id, downstream_id, "COPYING")
            _ = subprocess.check_output(rsync_cmd, shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            logger.fatal("The following command failed with return code %s: %s",
                         e.returncode, ' '.join(rsync_cmd))
            logger.fatal("Output: %s", e.output.decode())
            logger.fatal("Exiting")
            update_mongodb(db, run_number, analysis_id, downstream_id, "ERROR")
            sys.exit(1)
        #Update the mongoDB for successful data transfer
        #Update jobs (multisample) in pipeline_runs collection and replace the
        #jobid instead of SUCCESS in the following mongo status update
        logger.info("data transfer successfully completed for %s from %s", mux, run_number)
        update_mongodb(db, run_number, analysis_id, downstream_id, "SUCCESS")
        return True
    else:
        return False

def main():
    """main function
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-1', "--break-after-first", action='store_true',
                        help="Only process first run returned")
    parser.add_argument('-n', "--dry-run", action='store_true',
                        help="Don't run anything")
    default = 14
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
    trigger = 0
    for run in run_records:
        for mux, info in run.items():
            find = start_data_transfer(db, mux, info, site='nscc')
            if find:
                trigger = 1
            else:
                #send email alert
                logger.warning("MUX %s, already exists, please check", mux)
                continue
        if args.break_after_first and trigger == 1:
            logger.info("Stopping after first run")
            break

if __name__ == "__main__":
    main()
