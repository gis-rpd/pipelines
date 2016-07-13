#!/usr/bin/env python3
"""downstream jobs are delegated in pipeline_runs collection
"""
# standard library imports
import logging
import sys
import os
import argparse
import getpass
import glob
from collections import namedtuple

#--- third party imports
#
import requests
#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from rest import rest_services
from pipelines import mongodb_conn
from pipelines import generate_window, send_mail
from pipelines import get_machine_run_flowcell_id

LibUnit = namedtuple('LibUnit', ['mux_id', 'run_id', 'fastqs', 'pipeline_name',
                                 'pipeline_version', 'pipeline_params', 'out_dir', 'site', 'ctime'])
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

def check_fastq(fastq_data_dir, libid):
    """Check if fastq data available for library
    """
    fastq_list = (os.path.join(fastq_data_dir, "*libid", "*fastq.gz")).replace("libid", libid)
    fastq_data = glob.glob(fastq_list)
    if len(fastq_data) > 0:
        return (True, fastq_data)
    else:
        return (False, None)


def mongodb_update_runcomplete(run_num_flowcell, analysis_id, mux_id, insert_id, connection):
    """Change the status to DELEGATED in runcomplete collection of MongoDB
    """
    try:
        db = connection.gisds.runcomplete
        db.update({"run": run_num_flowcell, \
            'analysis.analysis_id' : analysis_id, \
            'analysis.per_mux_status.mux_id' : mux_id}, \
            {"$set": {insert_id: "DELEGATED", }})
    except pymongo.errors.OperationFailure:
        logger.fatal("MongoDB OperationFailure")
        return False
    else:
        return True


def mongodb_insert_libjob(lib, lib_info, connection):
    """Insert records into pipeline_runs collection of MongoDB
    """
    try:
        db = connection.gisds.pipeline_runs
        db.insert_one({"lib_id": lib, \
            "mux_id":lib_info.mux_id, \
            "run_id":lib_info.run_id, \
            "ctime":lib_info.ctime, \
            "fastqs":lib_info.fastqs, \
            "pipeline_name":lib_info.pipeline_name, \
            "pipeline_version":lib_info.pipeline_version, \
            "pipeline_params":lib_info.pipeline_params, \
            "out_dir":lib_info.out_dir, \
            "site":lib_info.site \
            })
    except pymongo.errors.OperationFailure:
        logger.fatal("mongoDB OperationFailure")
        return False
    else:
        return True


def mongodb_remove_muxjob(mux_id, run_id, ctime, connection):
    """Delete libraries from MUX, runID and ctime
    """
    try:
        db = connection.gisds.runcomplete
        db.remove({"run_id": run_id, "mux_id": mux_id, "ctime": ctime})
    except pymongo.errors.OperationFailure:
        logger.fatal("mongoDB OperationFailure")
        sys.exit(1)


def get_lib_details(run_num_flowcell, mux_list, testing):
    """Lib info collection from ELM per run
    """
    _, run_num, _ = get_machine_run_flowcell_id(run_num_flowcell)
    # Call rest service to get component libraries
    if testing:
        rest_url = rest_services['run_details']['testing'].replace("run_num", run_num)
        logger.info("development server")
    else:
        rest_url = rest_services['run_details']['production'].replace("run_num", run_num)
        logger.info("production server")
    response = requests.get(rest_url)
    if response.status_code != requests.codes.ok:
        response.raise_for_status()
    rest_data = response.json()
    logger.debug("rest_data from %s: %s", rest_url, rest_data)
    pipeline_params_dict = {}
    if rest_data.get('runId') is None:
        logger.info("JSON data is empty for run num %s", run_num)
        return pipeline_params_dict
    for mux_id, out_dir in mux_list:
        fastq_data_dir = os.path.join(out_dir[0], 'out', "Project_"+mux_id)
        if os.path.exists(fastq_data_dir):
            for rows in rest_data['lanes']:
                if mux_id in rows['libraryId']:
                    params = {}
                    ctime, _ = generate_window(1)
                    if "MUX" in rows['libraryId']:
                        for child in rows['Children']:
                            params['genome'] = child['genome']
                            params['libtech'] = child['libtech']
                            if child.get('SNV_ROI') is not None:
                                params['SNV_ROI'] = child.get('SNV_ROI')
                            status, fastq_list = check_fastq(fastq_data_dir, child['libraryId'])
                            if status:
                                info = LibUnit(rows['libraryId'], run_num_flowcell, \
                                    fastq_list, child['Analysis'], None, params,  \
                                    run_num_flowcell, 'gis', ctime)
                                pipeline_params_dict[child['libraryId']] = info
                    else:
                        params['genome'] = rows['genome']
                        params['libtech'] = rows['libtech']
                        if rows.get('SNV_ROI') is not None:
                            params['SNV_ROI'] = rows.get('SNV_ROI')
                        status, fastq_list = check_fastq(fastq_data_dir, rows['libraryId'])
                        if status:
                            info = LibUnit(rows['libraryId'], run_num_flowcell, \
                                    fastq_list, rows['Analysis'], None, params, \
                                    run_num_flowcell, 'gis', ctime)
                            pipeline_params_dict[rows['libraryId']] = info
    return pipeline_params_dict


def main():
    """main function
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-n', "--dry-run", action='store_true',
                        help="Don't run anything")
    parser.add_argument('-t', "--testing", action='store_true',
                        help="Use MongoDB test-server here and when calling bcl2fastq wrapper (-t)")
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
    # and https://gist.github.com/andreas-wilm/b6031a84a33e652680d4
    # script -vv -> DEBUG
    # script -v -> INFO
    # script -> WARNING
    # script -q -> ERROR
    # script -qq -> CRITICAL
    # script -qqq -> no logging at all
    logger.setLevel(logging.WARN + 10*args.quiet - 10*args.verbose)

    user_name = getpass.getuser()
    if user_name != "userrig":
        logger.warning("Not a production user. Skipping MongoDB update")
        sys.exit(0)

    connection = mongodb_conn(args.testing)
    if connection is None:
        sys.exit(1)
    db = connection.gisds.runcomplete
    epoch_present, epoch_back = generate_window(args.win)
    results = db.find({"analysis.per_mux_status" : {"$exists": True},
                       "timestamp": {"$gt": epoch_back, "$lt": epoch_present}})
    logger.info("Found %s runs", results.count())
    run_list = {}
    mongo_db_ref = {}
    for record in results:
        run_number = record['run']
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
                mux_db_id = "analysis.{}.per_mux_status.{}.DownstreamSubmission".format(
                    analysis_count, mux_count)
                if mux_status.get('Status') == "SUCCESS" and \
                    mux_status.get('DownstreamSubmission', None) == "TODO":
                    mongo_list = (mux_id, mux_db_id, analysis_id)
                    mongo_db_ref.setdefault(run_number, []).append(mongo_list)
                    mux_list.setdefault(mux_id, []).append(out_dir)
        for mux_id, out_dir in mux_list.items():
            mux_list_success = mux_list[mux_id]
            #Check if MUX has been analyzed more then 1 time successfully
            if len(mux_list_success) > 1:
                body = "{} has been analyzed more than 1 time successfully..".format(mux_id) \
                    + "delegator is skipping the downstream analysis under {}. Please" \
                    "check the results.".format(mux_list_success)
                subject = "Downstream delegator skipped job submission for {}".format(mux_id)
                if args.testing:
                    subject += " (testing)"
                send_mail(subject, body, toaddr='veeravallil', ccaddr=None)
                continue
            mux_info = (mux_id, out_dir)
            run_list.setdefault(run_number, []).append(mux_info)
    for run_num_flowcell, mux_list in run_list.items():
        update_status = True
        pipeline_params_dict = get_lib_details(run_num_flowcell, mux_list, args.testing)
        if not bool(pipeline_params_dict):
            logger.warning("pipeline_paramas_dict is empty for run num %s", run_num_flowcell)
            continue
        for lib, lib_info in pipeline_params_dict.items():
            if args.dry_run:
                logger.warning("Skipping job delegation for %s from %s", \
                    lib_info.mux_id, lib_info.run_id)
                continue
            res = mongodb_insert_libjob(lib, lib_info, connection)
            if not res:
                logger.critical("Skipping rest of analysis job submission" \
                    "for %s from %s", lib, lib_info.run_id)
                subject = "Downstream delegator failed job submission for" \
                    "{}".format(lib_info.mux_id)
                if args.testing:
                    subject += " (testing)"
                body = "Downstream delegator failed to insert job submission for" \
                    "{}".format(lib_info.mux_id)
                send_mail(subject, body, toaddr='veeravallil', ccaddr=None)
                update_status = False
                logger.warning("Clean up the database for mux %s from run %s and ctime %s", \
                    lib_info.mux_id, lib_info.run_id, lib_info.ctime)
                mongodb_remove_muxjob(lib_info.mux_id, lib_info.run_id, \
                    lib_info.ctime, connection)
                break
        if not args.dry_run and update_status:
            value = mongo_db_ref[run_num_flowcell]
            for mux_id, insert_id, analysis_id in value:
                logger.info("Update mongoDb runComplete for %s and runnumber is %s" \
                    "and id is %s and analysis_id %s", run_num_flowcell, mux_id, \
                    insert_id, analysis_id)
                res = mongodb_update_runcomplete(run_num_flowcell, analysis_id, mux_id, \
                    insert_id, connection)
                if not res:
                    logger.critical("Skipping rest of analysis job submission for %s" \
                        "from %s", mux_id, run_num_flowcell)
                    subject = "Downstream delegator failed job submission for {}" \
                        .format(mux_id)
                    if args.testing:
                        subject += " (testing)"
                    body = "Downstream delegator failed to insert job submission for" \
                        "{}".format(mux_id)
                    send_mail(subject, body, toaddr='veeravallil', ccaddr=None)
                    update_status = False
                    break
    connection.close()

if __name__ == "__main__":
    logger.info("Send email to Users and NGSP")
    main()

