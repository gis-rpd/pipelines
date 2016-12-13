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
import pymongo
import yaml

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from services import rest_services
from mongodb import mongodb_conn
from pipelines import generate_window
from pipelines import get_site
from pipelines import send_mail
from pipelines import get_machine_run_flowcell_id
from pipelines import get_downstream_outdir
from readunits import key_for_readunit

ReadUnit = namedtuple('ReadUnit', ['run_id', 'flowcell_id', 'library_id',
                                   'lane_id', 'rg_id', 'fq1', 'fq2'])

__author__ = "Lavanya Veeravalli"
__email__ = "veeravallil@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


CRONJOB_BASE = {
    'GIS': '/mnt/projects/rpd/pipelines/',
    'NSCC': '/home/users/astar/gis/gisshared/rpd/pipelines/'
}

PIPELINE_MAPPER = {
    'bwa_default_mapping': 'mapping/BWA-MEM',
    'bwa_aln_mapping': 'mapping/BWA-MEM',
}

# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)

def check_fastq(fastq_data_dir, libid, laneId):
    """Check if fastq data available for library
    """
    fastq_list = (os.path.join(fastq_data_dir, "*libid", "*fastq.gz")).replace("libid", libid)
    fastq_data = glob.glob(fastq_list)
    fq1 = fq2 = None
    if len(fastq_data) > 0:
        for file in fastq_data:
            base = os.path.basename(file)
            if "L00laneId_R1_".replace("laneId", laneId) in base:
                fq1 = file
            elif "L00laneId_R2_".replace("laneId", laneId) in base:
                fq2 = file
        if fq2:
           return (True, fq1, fq2)
        else:
            return (True, fq1, None)
    else:
        return (False, None, None)

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

def mongodb_insert_libjob(lib_info, connection):
    """Insert records into pipeline_runs collection of MongoDB
    """
    try:
        db = connection.gisds.pipeline_runs
        db.insert_one(lib_info)
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

def get_reference_info(analysis, pipeline_version, ref, site=None, basedir_map=CRONJOB_BASE):
    """Get the reference yaml for each library
    """
    if not site:
        site = get_site()
    if site not in basedir_map:
        raise ValueError(site)
    basedir = basedir_map[site]
    try:
        new_analysis = PIPELINE_MAPPER[analysis]
    except KeyError as e:
        logger.warning(str(e) + " Pipeline not mappped to newer version")
        return None
    ref_info = glob.glob(os.path.join(basedir, pipeline_version, \
        new_analysis, 'cfg', '*' + ref+'.yaml'))
    if ref_info:
        with open(ref_info[0], 'r') as f:
            try:
                doc = yaml.load(f)
                return doc
            except yaml.YAMLError as exc:
                print(exc)
                return None
    else:
        return None

def get_pipeline_version(pipeline_version):
    """ Get pipeline version
    """
    if pipeline_version:
        return pipeline_version
    else:
        return "current"

def get_lib_details(run_num_flowcell, mux_list, testing):
    """Lib info collection from ELM per run
    """
    _, run_num, flowcellid = get_machine_run_flowcell_id(run_num_flowcell)
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
    sample_info = {}
    mux_analysis_list = set()
    if rest_data.get('runId') is None:
        logger.info("JSON data is empty for run num %s", run_num)
        return sample_info
    ctime, _ = generate_window(1)
    for mux_id, out_dir in mux_list:
        fastq_data_dir = os.path.join(out_dir[0], 'out', "Project_"+mux_id)
        if os.path.exists(fastq_data_dir):
            for rows in rest_data['lanes']:
                if mux_id in rows['libraryId']:
                    logger.info("Checking the pipeline params for %s from run number %s", \
                        rows['libraryId'], run_num)
                    if "MUX" in rows['libraryId']:
                        for child in rows['Children']:
                            if child['Analysis'] != "Sequence only":
                                mux_analysis_list.add(mux_id)
                                sample_dict = {}
                                sample = child['libraryId']
                                sample_dict['requestor'] = rows['requestor']
                                sample_dict['ctime'] = ctime
                                sample_dict['pipeline_name'] = child['Analysis']
                                pipeline_version = get_pipeline_version(child['pipeline_version'] \
                                    if 'pipeline_version' in rows else None)
                                sample_dict['pipeline_version'] = pipeline_version
                                sample_dict['pipeline_params'] = 'params'
                                out_dir = get_downstream_outdir(
                                    sample_dict['requestor'], sample_dict['pipeline_name'],
                                    pipeline_version=sample_dict['pipeline_version'])
                                ref_info = get_reference_info(child['Analysis'], \
                                    sample_dict['pipeline_version'], child['genome'])
                                if not ref_info:
                                    continue
                                sample_dict['references'] = ref_info
                                sample_dict['out_dir'] = out_dir
                                readunits_dict = {}
                                status, fq1, fq2 = check_fastq(fastq_data_dir, child['libraryId'],\
                                    rows['laneId'])
                                if status:
                                    ru = ReadUnit(run_num_flowcell, flowcellid, child['libraryId'],\
                                        rows['laneId'], None, fq1, fq2)
                                    k = key_for_readunit(ru)
                                    readunits_dict[k] = dict(ru._asdict())
                                    sample_dict['readunits'] = readunits_dict
                                    if sample_info.get(sample, {}).get('readunits'):
                                        sample_info[sample]['readunits'].update(readunits_dict)
                                    else:
                                        sample_info[sample] = sample_dict
                    else:
                        if rows['Analysis'] != "Sequence only":
                            mux_analysis_list.add(mux_id)
                            sample = rows['libraryId']
                            status, fq1, fq2 = check_fastq(fastq_data_dir, rows['libraryId'], \
                                rows['laneId'])
                            if status:
                                sample_dict = {}
                                sample_dict['requestor'] = rows['requestor']
                                sample_dict['ctime'] = ctime
                                sample_dict['pipeline_name'] = rows['Analysis']
                                pipeline_version = get_pipeline_version(rows['pipeline_version'] \
                                    if 'pipeline_version' in rows else None)
                                sample_dict['pipeline_version'] = pipeline_version
                                sample_dict['pipeline_params'] = 'params'
                                out_dir = get_downstream_outdir(
                                    sample_dict['requestor'], sample_dict['pipeline_name'],
                                    pipeline_version=sample_dict['pipeline_version'])
                                ref_info = get_reference_info(rows['Analysis'], \
                                    sample_dict['pipeline_version'], rows['genome'])
                                if not ref_info:
                                    continue
                                sample_dict['references'] = ref_info
                                sample_dict['out_dir'] = out_dir
                                readunits_dict = {}
                                ru = ReadUnit(run_num_flowcell, flowcellid, rows['libraryId'], \
                                    rows['laneId'], None, fq1, fq2)
                                k = key_for_readunit(ru)
                                readunits_dict[k] = dict(ru._asdict())
                                sample_dict['readunits'] = readunits_dict
                                sample_info[sample] = sample_dict
    return sample_info, mux_analysis_list
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
                    mux_status.get('DownstreamSubmission') == "TODO":
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
        pipeline_params_dict, mux_analysis_list = get_lib_details(run_num_flowcell, \
            mux_list, args.testing)
        if not bool(pipeline_params_dict):
            logger.warning("pipeline params is empty for run num %s", run_num_flowcell)
            continue
        for lib, lib_info in pipeline_params_dict.items():
            readunits_list = list()
            for outer_key in lib_info:
                if outer_key == 'readunits':
                    for inner_key in lib_info[outer_key]:
                        readunits_list.append(inner_key)
            lib_info['samples'] = {}
            lib_info['samples'][lib] = readunits_list
            if args.dry_run:
                logger.warning("Skipping job delegation for %s", \
                    lib)
                continue
            res = mongodb_insert_libjob(lib_info, connection)
            if not res:
                logger.critical("Skipping rest of analysis job submission" \
                     "for %s from %s", lib, lib_info.run_id)
                subject = "Downstream delegator failed job submission for" \
                    "{}".format(lib)
                if args.testing:
                    subject += " (testing)"
                body = "Downstream delegator failed to insert job submission for" \
                    "{}".format(lib)
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
                if mux_id in mux_analysis_list:
                    logger.info("Update mongoDb pipeline_runs for mux_id %s from run number %s" \
                        "and analysis_id is %s", mux_id, run_num_flowcell, analysis_id)
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
