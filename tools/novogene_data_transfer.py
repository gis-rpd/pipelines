#!/usr/bin/env python3
""" Cronjob to copy Novogene fastq data from GIS to NSCC
"""
# standard library imports
import logging
import sys
import os
import argparse
import subprocess
import glob
from collections import namedtuple

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
from pipelines import generate_window, get_machine_run_flowcell_id
from config import novogene_conf
from readunits import key_for_readunit

ReadUnit = namedtuple('ReadUnit', ['run_id', 'flowcell_id', 'library_id',
                                   'lane_id', 'rg_id', 'fq1', 'fq2'])
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

def runs_from_db(connection, win=14):
    """Get the runs from pipeline_run collections"""
    db = connection.gisds.runcomplete
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
        run_records = {}
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
                    mux_info = (run_number, downstream_id, analysis_id, out_dir)
                    if mux_id in run_records:
                        #Send email the above message
                        logger.info("MUX %s from %s has been analyzed more than 1 time \
                            succeessfully, send email", mux_id, run_number)
                        del run_records[mux_id]
                    else:
                        run_records[mux_id] = mux_info
        if run_records:
            yield run_records

def update_downstream_mux(connection, run_number, analysis_id, downstream_id, Status):
    """Update the status in the mongoDB runcomplete collection
    """
    db = connection.gisds.runcomplete
    try:
        db.update({"run": run_number, 'analysis.analysis_id' : analysis_id},
                  {"$set": {downstream_id: Status,}})
    except pymongo.errors.OperationFailure:
        logger.fatal("MongoDB OperationFailure")
        sys.exit(1)

def insert_muxjob(connection, mux, job):
    """Insert records into pipeline_runs collection of MongoDB
    """
    try:
        db = connection.gisds.pipeline_runs_copy
        _id = db.insert_one(job)
        job_id = _id.inserted_id
        logger.info("Job inserted for MUX %s", mux)
    except pymongo.errors.OperationFailure:
        logger.fatal("mongoDB OperationFailure")
        sys.exit(1)
    if job_id:
        return job_id

def get_mux_details(run_number, mux_id, fastq_dest):
    sample_list = glob.glob(os.path.join(fastq_dest, "*"+ mux_id, 'Sample_*'))
    _, _, flowcellid = get_machine_run_flowcell_id(run_number)
    sample_info = {}
    readunits_dict = {}
    samples_dict = {}
    for sample in sample_list:
        sample_fastq_list = glob.glob(os.path.join(sample, '*fastq.gz'))
        #Check if R1 and R2 pairs for each lane are equal
        if len(sample_fastq_list)%2 == 0:
            lane_dict = {}
            for x in sorted(sample_fastq_list):
                lane_id = os.path.basename(x).split('_')
                indices = [i for i, s in enumerate(lane_id) if 'L00' in s]
                lane_dict.setdefault(lane_id[indices[0]][-1], []).append(x)
        for lane, v in lane_dict.items():
            lib = (os.path.basename(sample).split('_')[1])
            R1 = [i for i, s in enumerate(v) if '_R1_' in s]
            R2 = [i for i, s in enumerate(v) if '_R2_' in s]
            fq1 = v[R1[0]]
            fq2 = v[R2[0]]
            if not fq1 and not fq2:
                logger.critical("Please check the data integrity for %s from %s", \
                    mux_id, run_number)
                #send_mail
                sys.exit(1)
            ru = ReadUnit(run_number, flowcellid, lib, lane, None, fq1, fq2)
            k = key_for_readunit(ru)
            readunits_dict[k] = dict(ru._asdict())
            sample_info['readunits'] = readunits_dict
            samples_dict.setdefault(lib, []).append(k)
            sample_info['samples'] = samples_dict
    return sample_info

def start_data_transfer(connection, mux, mux_info, site):
    """ Data transfer from source to destination
    """
    bcl_path = mux_info[3]
    fastq_src = os.path.join(bcl_path, "out", "Project_"+mux)
    bcl_dir = os.path.basename(mux_info[3])
    run_number = mux_info[0]
    analysis_id = mux_info[2]
    downstream_id = mux_info[1]
    fastq_dest = os.path.join(novogene_conf['FASTQ_DEST'][site], mux, run_number, bcl_dir)
    rsync_cmd = '/usr/bin/rsync -va %s %s' % (fastq_src, fastq_dest)
    if not os.path.exists(fastq_dest):
        try:
            os.makedirs(fastq_dest)
            logger.info("data transfer started for %s from %s", mux, run_number)
            update_downstream_mux(connection, run_number, analysis_id, downstream_id, "COPYING")
            _ = subprocess.check_output(rsync_cmd, shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            logger.fatal("The following command failed with return code %s: %s",
                         e.returncode, ' '.join(rsync_cmd))
            logger.fatal("Output: %s", e.output.decode())
            logger.fatal("Exiting")
            #Send_mail
            #Delete the partial info being rsync
            update_downstream_mux(connection, run_number, analysis_id, downstream_id, "ERROR")
            sys.exit(1)
        #Update the mongoDB for successful data transfer
        sample_info = get_mux_details(run_number, mux, fastq_dest)
        job = {}
        job['sample_cfg'] = {}
        for outer_key, outer_value in sample_info.items():
            ctime, _ = generate_window(1)
            job['sample_cfg'].update({outer_key:outer_value})
            job['site'] = site
            job['pipeline_name'] = 'custom/SG10K'
            job['pipeline_version'] = 'current'
            job['ctime'] = ctime
        logger.info("data transfer successfully completed for %s from %s", mux, run_number)
        job_id = insert_muxjob(connection, mux, job)
        update_downstream_mux(connection, run_number, analysis_id, downstream_id, job_id)
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
    if is_devel_version() or args.testing:
        mail_to = 'veeravallil'# domain added in mail function
    else:
        mail_to = 'rpd'
    run_records = runs_from_db(connection, args.win)
    trigger = 0
    for run in run_records:
        for mux, mux_info in run.items():
            if args.dry_run:
                logger.warning("Skipping job delegation for %s", mux)
                continue
            res = start_data_transfer(connection, mux, mux_info, site='nscc')
            if res:
                trigger = 1
            else:
                #send_mail alert
                logger.warning("%s from %s, already exists, please check", mux, mux_info[0])
                continue
        if args.break_after_first and trigger == 1:
            logger.info("Stopping after first run")
            break

if __name__ == "__main__":
    main()
