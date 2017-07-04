#!/usr/bin/env python3
"""Basically a pipeline starter and logger

see https://bitbucket.org/liewjx/rpd
"""

#--- standard library imports
#
import logging
import sys
import os
import argparse
import glob
from datetime import datetime
import tempfile
import subprocess

#--- third party imports
#
#import yaml
import dateutil.parser
import yaml
from bson.objectid import ObjectId

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
from pipelines import snakemake_log_status
from pipelines import PipelineHandler
from pipelines import is_devel_version
from pipelines import get_site
from starterflag import StarterFlag
path_devel = LIB_PATH + "/../"


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2017 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# FIXME should go to yaml in etc/
PIPELINE_PATH_BASE = {
    'GIS': {
        'production': '/mnt/projects/rpd/pipelines/',
        'devel': path_devel},
    'NSCC': {
        'devel': '/home/users/astar/gis/gisshared/rpd/pipelines.git/',
        'production': '/home/users/astar/gis/gisshared/rpd/pipelines/'}
}

# global logger
LOGGER = logging.getLogger(__name__)
HANDLER = logging.StreamHandler()
HANDLER.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
LOGGER.addHandler(HANDLER)


# warning thresholds
THRESHOLD_H_SINCE_LAST_TIMESTAMP = 24
THRESHOLD_H_SINCE_START = 72

def start_cmd_execution(record, site, out_dir, testing):
    """ Start the analysis
    """
    pipeline_params = " "
    extra_conf = " --extra-conf "
    extra_conf += "db-id:" + str(record['_id'])
    extra_conf += " requestor:" + record['requestor']
    # sample_cfg and references_cfg
    references_cfg = ""
    sample_cfg = ""
    for outer_key, outer_value in record.items():
        if outer_key == 'sample_cfg':
            LOGGER.info("write temp sample_config")
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', prefix='sample_cfg_', \
                delete=False) as fh:
                sample_cfg = fh.name
                yaml.dump(outer_value, fh, default_flow_style=False)
        elif outer_key == 'references_cfg':
            LOGGER.info("write temp reference_config")
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', prefix='references_cfg_', \
                delete=False) as fh:
                references_cfg = fh.name
                yaml.dump(outer_value, fh, default_flow_style=False)
        elif outer_key == 'cmdline':
            LOGGER.info("pipeline_cmd")
            for key, value in outer_value.items():
                pipeline_params += " --" + key + " " + value
    #pipeline path for production and testing
    if is_devel_version():
        pipeline_version = ""
    else:
        pipeline_version = record['pipeline_version'].split(".")[0]
    pipeline_path = get_pipeline_path(site, record['pipeline_name'], \
        pipeline_version)
    pipeline_script = os.path.join(pipeline_path, (os.path.split(pipeline_path)[-1] + ".py"))
    if not pipeline_script:
            LOGGER.critical("There seems to be trouble in executing cmd_line for JobId: {}".format(str(record['_id'])))
    pipeline_cmd = pipeline_script + " --sample-cfg " + sample_cfg  + " -o " + out_dir + " --db-logging y"
    if not sample_cfg:
        LOGGER.critical("Job doesn't have sample_cfg %s", str(record['_id']))
        sys.exit(1)
    if references_cfg:
        ref_params = " --references-cfg " + references_cfg
        pipeline_cmd += ref_params
    if pipeline_params:
        pipeline_cmd += pipeline_params
    if extra_conf:
        pipeline_cmd += extra_conf
    try:
        LOGGER.info(pipeline_cmd)
        _ = subprocess.check_output(pipeline_cmd, stderr=subprocess.STDOUT, shell=True)
        return True
    except subprocess.CalledProcessError as e:
        LOGGER.fatal("The following command failed with return code %s: %s",
            e.returncode, ' '.join(pipeline_cmd))
        LOGGER.fatal("Output: %s", e.output.decode())
        return False
    
def get_pipeline_path(site, pipeline_name, pipeline_version):
    """ get the pipeline path
    """
    basedir_map = PIPELINE_PATH_BASE
    if site not in basedir_map:
        raise ValueError(site)
    if is_devel_version():
        basedir = basedir_map[site]['devel']
        pipeline_path = os.path.join(basedir, pipeline_name)
        return pipeline_path
    else:
        basedir = basedir_map[site]['production']
        pipeline_path = glob.glob(os.path.join(basedir, "*"+pipeline_version, pipeline_name))
        return pipeline_path[0]

def list_starterflags(path):
    """list starter flag files in path
    """
    return glob.glob(os.path.join(
        path, StarterFlag.pattern.format(timestamp="*")))

def set_completion_if(dbcol, dbid, out_dir, dryrun=False):
    """Update values for already started job based on log file in out_dir
    """

    rec = dbcol.find_one({"_id": dbid})
    assert rec, "No objects found with db-id {}".format(dbid)

    assert rec.get('execution'), ("Looks like job %s was never started", dbid)
    old_status = rec['execution'].get('status')
    start_time = rec['execution'].get('start_time')
    out_dir = rec['execution'].get('out_dir')
    assert old_status and start_time, (
        "Job start for %s was not logged properly (status or start_time not set)", dbid)
    assert rec['execution']['out_dir'] == out_dir

    snakelog = os.path.join(out_dir, PipelineHandler.MASTERLOG)
    LOGGER.info("Checking snakemake log %s for status of job %s", snakelog, dbid)
    assert os.path.exists(snakelog), (
        "Expected snakemake log file %s for job %s doesn't exist.", snakelog, dbid)

    status, end_time = snakemake_log_status(snakelog)
    LOGGER.info("Job %s has status %s (end time %s)",
                dbid, status, end_time)
    if dryrun:
        LOGGER.info("Skipping DB update due to dryrun option")
        return

    if status == "SUCCESS":
        assert end_time
        dbcol.update_one({"_id": ObjectId(dbid)},
                         {"$set": {"execution.status": "SUCCESS",
                                   "execution.end_time": end_time}})
    elif status == "ERROR":
        assert end_time
        dbcol.update_one({"_id": ObjectId(dbid)},
                         {"$set": {"execution.status": "FAILED",
                                   "execution.end_time": end_time}})
    else:
        if end_time:# without status end_time means last seen time in snakemake
            delta = datetime.now() - dateutil.parser.parse(end_time)
            diff_min, _ = divmod(delta.days * 86400 + delta.seconds, 60)
            diff_hours = diff_min/60.0
            if diff_hours > THRESHOLD_H_SINCE_LAST_TIMESTAMP:
                LOGGER.warning("Last log update for job id %s was %s hours ago. That's a bit long.", dbid, diff_hours)
        # Re-convert start_time from isoformat as it happens in generate_timestamp()
        delta = datetime.now() - dateutil.parser.parse(start_time.replace("-", ":"))
        diff_min, _ = divmod(delta.days * 86400 + delta.seconds, 60)
        diff_hours = diff_min/60.0
        if diff_hours > THRESHOLD_H_SINCE_START:
            LOGGER.warning("Job id %s was started %s hours ago. That's a bit long", dbid, diff_hours)


def set_started(dbcol, dbid, start_time, dryrun=False):
    """Update records for started or restarted analysis
    """
    rec = dbcol.find_one({"_id": ObjectId(dbid)})
    assert rec, "No objects found with db-id {}".format(dbid)

    # determine if this is a start or a restart (or a mistake)
    assert rec.get('execution')
    if rec['execution'].get('start_time'):
        assert rec['execution'].get('status')
        mode = 'restart'
    else:
        mode = 'start'

    LOGGER.info("Updating %sed job %s", mode, dbid)
    if dryrun:
        LOGGER.info("Skipping DB update due to dryrun option")
        return
    out_dir = rec['execution'].get('out_dir')
    if mode == 'start':
        res = dbcol.update_one(
            {"_id": ObjectId(dbid)},
            {"$set": {"execution": {"start_time" : start_time, "status" : "STARTED", "out_dir" : out_dir}}})
        assert res.modified_count == 1, (
            "Modified {} documents instead of 1".format(res.modified_count))

    elif mode == 'restart':
        res = dbcol.update_one({"_id": ObjectId(dbid)},
                               {"$set": {"execution.status": "RESTART"}})
        assert res.modified_count == 1, (
            "Modified {} documents instead of 1".format(res.modified_count))

        res = dbcol.update_one({"_id": ObjectId(dbid)},
                               {"$unset": {"execution.end_time": ""}})
        assert res.modified_count == 1, (
            "Modified {} documents instead of 1".format(res.modified_count))

        res = dbcol.update_one({"_id": ObjectId(dbid)},
                               {"$inc":{"execution.num_restarts": 1}})
        assert res.modified_count == 1, (
            "Modified {} documents instead of 1".format(res.modified_count))

    else:
        raise ValueError(mode)


def main():
    """main function
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-n', "--dryrun", action='store_true',
                        help="Don't actually update DB (best used in conjunction with -v -v)")
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
    #LOGGER.info("Database connection established")
    dbcol = connection.gisds.pipeline_runs
    site = get_site()
    epoch_now, epoch_then = generate_window(args.win)
    cursor = dbcol.find({"ctime": {"$gt": epoch_then, "$lt": epoch_now}, "site" : site})
    LOGGER.info("Looping through {} jobs".format(cursor.count()))
    for job in cursor:
        dbid = job['_id']

        # only set here to avoid code duplication below
        try:
            out_dir = job['execution']['out_dir']
        except KeyError:
            out_dir = None

        # no execution dict means start a new analysis
        if not job.get('execution'):
            LOGGER.info('Job {} to be started'.format(dbid))
            # determine out_dir and set in DB
            # out_dir_override will take precedence over generating out_dir with get_downstream_outdir function 
            if job.get('out_dir_override'):
                out_dir = job.get('out_dir_override')
                assert not os.path.exists(out_dir), ("Direcotry already exists {}").format(out_dir)
            else:
                out_dir = get_downstream_outdir(
                    job['requestor'], job['pipeline_name'], job['pipeline_version'])
            # Note, since execution (key) exists, accidental double
            # starts are prevented even before start time etc is
            # logged via flagfiles.  No active logging here so that
            # flag files logging just works.

            if args.dryrun:
                LOGGER.info("Skipping dry run option")
                continue
            status = start_cmd_execution(job, site, out_dir, args.testing)
            if status:
                res = dbcol.update_one(
                    {"_id": ObjectId(dbid)},
                    {"$set": {"execution.out_dir": out_dir}})
                assert res.modified_count == 1, (
                    "Modified {} documents instead of 1".format(res.modified_count))
            else:
                LOGGER.warning("Job {} could not be started".format(dbid))
        elif list_starterflags(out_dir):# out_dir cannot be none because it's part of execution dict 
            LOGGER.info('Job {} in {} started but not yet logged as such in DB'.format(
                dbid, out_dir))

            matches = list_starterflags(out_dir)
            assert len(matches) == 1, (
                "Got several starter flags in {}".format(out_dir))
            sflag = StarterFlag(matches[0])
            assert sflag.dbid == str(dbid)
            set_started(dbcol, sflag.dbid, str(sflag.timestamp), dryrun=args.dryrun)
            os.unlink(sflag.filename)

        elif job['execution'].get('status') in ['STARTED', 'RESTART']:
            LOGGER.info('Job %s in %s set as re|started so checking on completion', dbid, out_dir)
            set_completion_if(dbcol, dbid, out_dir, dryrun=args.dryrun)

        else:
            # job complete
            LOGGER.debug('Job %s in %s should be completed', dbid, out_dir)
    LOGGER.info("Successful program exit")

if __name__ == "__main__":
    main()
