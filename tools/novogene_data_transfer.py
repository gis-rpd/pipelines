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

#--- third party imports
#
import pymongo
import yaml

# project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from mongodb import mongodb_conn
from pipelines import is_production_user, is_devel_version, send_mail
from pipelines import generate_window, get_machine_run_flowcell_id
from pipelines import generate_timestamp
from config import novogene_conf
from readunits import readunits_for_sampledir

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

yaml.Dumper.ignore_aliases = lambda *args: True

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
                    continue
                mux_id = mux_status['mux_id']
                out_dir = analysis['out_dir']
                downstream_id = "analysis.{}.per_mux_status.{}.DownstreamSubmission".format(
                    analysis_count, mux_count)
                if mux_status.get('Status') == "SUCCESS" and \
                    mux_status.get('DownstreamSubmission') == "TODO":
                    mux_info = (run_number, downstream_id, analysis_id, out_dir)
                    if mux_id in run_records:
                        logger.info("MUX %s from %s has been analyzed more than 1 time \
                            succeessfully, please check", mux_id, run_number)
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

def check_mux_data_transfer_status(connection, mux_info):
    """Check MUX data is getting transferred
    """
    db = connection.gisds.runcomplete
    try:
        status = db.find({"run": mux_info[0], 'analysis.analysis_id' : mux_info[2],
                    mux_info[1] : "COPYING"})
        status_count = status.count()
    except pymongo.errors.OperationFailure:
        logger.fatal("MongoDB OperationFailure")
        sys.exit(1)
    if status_count == 1:
        return True

def insert_muxjob(connection, mux, job):
    """Insert records into pipeline_runs collection of MongoDB
    """
    try:
        db = connection.gisds.pipeline_runs
        _id = db.insert_one(job)
        job_id = _id.inserted_id
        logger.info("Job inserted for %s", mux)
    except pymongo.errors.OperationFailure:
        logger.fatal("mongoDB OperationFailure")
        sys.exit(1)
    if job_id:
        return job_id

def get_mux_details(run_number, mux_id, fastq_dest):
    """Fastq details etc for a MUX
    """
    sample_list = glob.glob(os.path.join(fastq_dest, "*"+ mux_id, 'Sample_*'))
    _, run_id, flowcell_id = get_machine_run_flowcell_id(run_number)
    readunits_dict = {}
    samples_dict = {}
    for sample_dir in sample_list:
        readunits = readunits_for_sampledir(sample_dir)
        # insert run id and flowcell id which can't be inferred from filename
        for ru in readunits.values():
            ru['run_id'] = run_id
            ru['flowcell_id'] = flowcell_id
        lib_ids = [ru['library_id'] for ru in readunits.values()]
        assert len(set(lib_ids)) == 1
        sample_name = lib_ids[0]
        assert sample_name not in samples_dict
        samples_dict[sample_name] = list(readunits.keys())
        for k, v in readunits.items():
            assert k not in readunits_dict
            readunits_dict[k] = v
    return {'samples': samples_dict,
        'readunits': readunits_dict}

def start_data_transfer(connection, mux, mux_info, site, mail_to):
    """ Data transfer from source to destination
    """
    run_number, downstream_id, analysis_id, bcl_path = mux_info
    fastq_src = os.path.join(bcl_path, "out", "Project_"+mux)
    bcl_dir = os.path.basename(bcl_path)
    if is_devel_version():
        fastq_dest = os.path.join(novogene_conf['FASTQ_DEST'][site]['devel'], \
            mux, run_number, bcl_dir)
        yaml_dest = os.path.join(novogene_conf['FASTQ_DEST'][site]['devel'], \
            mux, mux +"_multisample.yaml")
    else:
        fastq_dest = os.path.join(novogene_conf['FASTQ_DEST'][site]['production'], \
            mux, run_number, bcl_dir)
        yaml_dest = os.path.join(novogene_conf['FASTQ_DEST'][site]['production'], \
            mux, mux+ "_multisample.yaml")
    rsync_cmd = 'rsync -va %s %s' % (fastq_src, fastq_dest)
    if not os.path.exists(fastq_dest):
        try:
            os.makedirs(fastq_dest)
            logger.info("data transfer started for %s from %s", mux, run_number)
            st_time = generate_timestamp()
            update_downstream_mux(connection, run_number, analysis_id, downstream_id, \
                "COPYING_" + st_time)
            _ = subprocess.check_output(rsync_cmd, shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            body = "The following command failed with return code {}: {}". \
                format(e.returncode, rsync_cmd)
            subject = "rsync failed for {} from {}".format(mux, run_number)
            logger.fatal(body)
            logger.fatal("Output: %s", e.output.decode())
            logger.fatal("Exiting")
            #Send_mail
            send_mail(subject, body, toaddr=mail_to, ccaddr=None)
            #Delete the partial info being rsync
            update_downstream_mux(connection, run_number, analysis_id, downstream_id, "ERROR")
            sys.exit(1)
        #Update the mongoDB for successful data transfer
        sample_info = get_mux_details(run_number, mux, fastq_dest)
        #Touch rsync complete file
        with open(os.path.join(fastq_dest, "rsync_complete.txt"), "w") as f:
            f.write("")
        with open(yaml_dest, 'w') as fh:
            yaml.dump(dict(sample_info), fh, default_flow_style=False)
        job = {}
        job['sample_cfg'] = {}
        for outer_key, outer_value in sample_info.items():
            ctime, _ = generate_window(1)
            job['sample_cfg'].update({outer_key:outer_value})
            job['site'] = site
            job['pipeline_name'] = 'custom/SG10K'
            job['pipeline_version'] = 'current'
            job['ctime'] = ctime
            job['requestor'] = 'userrig'
        logger.info("data transfer successfully completed for %s from %s", mux, run_number)
        job_id = insert_muxjob(connection, mux, job)
        update_downstream_mux(connection, run_number, analysis_id, downstream_id, job_id)
        return True
    else:
        logger.critical("Mux %s from %s directory already exists under %s", mux, \
            run_number, fastq_dest)
        return False

def main():
    """main function
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-1', "--break-after-first", action='store_true',
                        help="Only process first run returned")
    parser.add_argument('-n', "--dry-run", action='store_true',
                        help="Don't run anything")
    default = "NSCC"
    parser.add_argument('-s', "--site", default=default,
                        help="site information (default = {})".format(default),
                        choices=['NSCC', 'GIS'])
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
                logger.warning("Skipping job delegation for %s from %s", mux, mux_info[0])
                continue
            #Check if mux data is getting transferred
            find = check_mux_data_transfer_status(connection, mux_info)
            if find:
                continue
            res = start_data_transfer(connection, mux, mux_info, args.site, mail_to)
            if res:
                trigger = 1
        if args.break_after_first and trigger == 1:
            logger.info("Stopping after first run")
            break
    # close the connection to MongoDB
    connection.close()

if __name__ == "__main__":
    main()
