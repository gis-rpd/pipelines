#!/usr/bin/env python3
""" Cronjob to archive Illumina runs
"""
# standard library imports
import logging
import sys
import os
import argparse
import tarfile
import shutil
import subprocess

# project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from mongodb import mongodb_conn
from pipelines import is_production_user
from pipelines import generate_window
from pipelines import is_devel_version
from pipelines import get_bcl_runfolder_for_runid
from pipelines import relative_isoformat_time
from utils import generate_timestamp

__author__ = "Lavanya Veeravalli"
__email__ = "veeravallil@gis.a-star.edu.sg"
__copyright__ = "2017 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"

TAR_PATH_BASE = { 
    'devel': '/mnt/projects/userrig/BENCHMARK_testing/test/'
}

# global logger
LOGGER = logging.getLogger(__name__)
HANDLER = logging.StreamHandler()
HANDLER.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
LOGGER.addHandler(HANDLER)


def run_ready_for_tarring(record, days=60):
    """Return runid if ready to be tarred/deleted

    If runs was aborted, return run id.
    If not succesful return None. 
    If completion was older than given days return run id
    """
    if not 'analysis' in record:
        return False
    last_analysis = record['analysis'][-1]
    status = last_analysis.get("Status")
    if status == "ABORTED":
        return True
    elif status != "SUCCESS":
        return False
    else:
        relative_days = relative_isoformat_time(last_analysis['end_time'])
        return relative_days > days
       


def check_tar_status_and_delete(db, record, days=60, dryrun=False):
    """Check run.tar status
    """
    run_num = record['run']
    if record['raw-delete'].get('tar') == "locked":
        # future version might want to keep a locked date, so that we can detect "zombies"
        LOGGER.info("%s tar ball creation in progress", run_num)
        return None

    relative_days = relative_isoformat_time(record['raw-delete'].get('timestamp_tar'))
    if relative_days > days:
        if record['raw-delete'].get('status') == "locked":
            LOGGER.info("Deletion of %s tar ball in progress", run_num)
            return None
        if dryrun:
            LOGGER.info("Skipping Deletion of %s due to dryrun option", run_num)
            return
        #set deletion.status = locked, update deletion.timestamp
        res = db.update_one(
            {"run": run_num},
            {"$set": {"raw-delete.status": "locked", "raw-delete.timestamp": generate_timestamp()}})
        assert res.modified_count == 1, (
            "Modified {} documents instead of 1".format(res.modified_count))
        #delete tar ball
        tar_file = record['raw-delete'].get('tar')
        md5sum_file = tar_file.replace(".tar", ".md5sum")
        assert os.path.exists(tar_file), "The run directory {} does not exists".format(tar_file)
        try:
            os.remove(tar_file)
            os.remove(md5sum_file)
        except OSError as e:
            LOGGER.critical("Error: %s - %s.", e.filename, e.strerror)
        #unset deletion.tar and deletion.timestamp_tar
        res = db.update_one(
            {"run": run_num},
            {"$unset": {"raw-delete.tar": "", "raw-delete.timestamp_tar": ""}})
        assert res.modified_count == 1, (
            "Modified {} documents instead of 1".format(res.modified_count))
        #set deletion.status = deleted, update deletion.timestamp
        res = db.update_one(
            {"run": run_num},
            {"$set": {"raw-delete.status": "deleted", "raw-delete.timestamp": \
                generate_timestamp()}})
        assert res.modified_count == 1, (
            "Modified {} documents instead of 1".format(res.modified_count))
        LOGGER.info("Deleted the tar ball for %s ", run_num)
        return True

def create_run_tar(db, run_num, tar_base_dir, delete_bcl=True):
    """compress bcl directory into a tar ball
    """
    rundir = get_bcl_runfolder_for_runid(run_num)
    if not os.path.exists(rundir):
        LOGGER.warning("%s does not exists", rundir)
        return

    #Set deletion.tar update timestamp
    res = db.update_one(
        {"run": run_num},
        {"$set": {"raw-delete.tar": "locked", "raw-delete.timestamp_tar": generate_timestamp()}})
    assert res.modified_count == 1, (
        "Modified {} documents instead of 1".format(res.modified_count))
    #Create tar ball and md5sum
    #assert os.path.isdir(rundir), "The run directory {} does not exists".format(rundir)

    run_tar = os.path.join(tar_base_dir, run_num) + ".tar"
    LOGGER.info("compression started %s ", run_tar)
    with tarfile.open(run_tar, "x") as tar:
        tar.add(rundir)
    md5sum_cmd = 'md5sum %s' % (run_tar)
    dest_md5sum = os.path.join(tar_base_dir, run_num) + ".md5sum"
    assert os.path.exists(run_tar), "Tar ball {} does not exists".format(run_tar)
    try:
        f = open(os.path.join(dest_md5sum), "w")
        _ = subprocess.call(md5sum_cmd, shell=True, stderr=subprocess.STDOUT, stdout=f)
        LOGGER.info("compression completed %s ", run_num)
        if delete_bcl:
            shutil.rmtree(rundir)
    except (subprocess.CalledProcessError, OSError) as e:
        LOGGER.fatal("The following command failed with return code %s: %s",
                     e.returncode, ' '.join(md5sum_cmd))
        LOGGER.fatal("Output: %s", e.output.decode())
        LOGGER.fatal("Exiting")
        return

    LOGGER.info("Deletion of bcl directory completed for %s ", run_num)
    #set deletion.tar = filename, update deletion.timestamp
    res = db.update_one(
        {"run": run_num},
        {"$set": {"raw-delete.tar": run_tar, "raw-delete.timestamp_tar": generate_timestamp()}})
    assert res.modified_count == 1, (
        "Modified {} documents instead of 1".format(res.modified_count))

def main():
    """main function
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-1', "--break-after-first", action='store_true',
                        help="Only process first run returned")
    parser.add_argument('-n', "--dryrun", action='store_true',
                        help="Don't run anything")

    # sequence of events:
    # 1. run-complete
    # 2. last(!)-bcl-run
    # 3. tar-created
    # 4. tar-deleted
    
    # DB windows to scan
    default = 210
    parser.add_argument('-w', '--win', type=int, default=default,
                        help="Number of days to look back in DB (default {})".format(default))
    # if the last bcl run is longer than x days ago, it will be tarred 
    default = 180
    parser.add_argument('-d', '--min-bcl-age', type=int, default=default,
                        help="Tar if last bcl analysis is older than x days (default {})".format(default))
    # if the tarball is older then x, it will be deleted
    default = 90
    parser.add_argument('-r', '--min-tar-age', type=int, default=default,
                        help="Delete tar ball if older than x days (default {})".format(default))
    parser.add_argument('-t', "--testing", action='store_true',
                        help="Use MongoDB test-server."
                        " WARNING: directories and deletion determined by devel flag presence"
                        " (%s)" % "present" if is_devel_version() else "not present")
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
    epoch_present, epoch_back = generate_window(args.win)
    results = db.find({"run" : {"$regex" : "^((?!NG00).)*$"},
                       "timestamp": {"$gt": epoch_back, "$lt": epoch_present}})
    LOGGER.info("Looping through %s jobs", results.count())
    trigger = 0
    for record in results:
        try:
            run_num = record['run']
        except KeyError:
            run_num = None
        if not record.get('raw-delete'):
            #Check run_status
            if run_ready_for_tarring(record, args.min_bcl_age):
                LOGGER.info("Create tar ball %s ", run_num)
                rundir = get_bcl_runfolder_for_runid(run_num)
                if not os.path.exists(rundir):
                    LOGGER.warning("Rundir %s does not exists", rundir)
                    continue
                if is_devel_version():
                    tarbasedir = TAR_PATH_BASE['devel']
                    delete_bcl = False
                else:
                    tarbasedir = os.path.dirname(rundir)
                    delete_bcl = True
                if args.dryrun:
                    LOGGER.warning("Skipping Create tar ball %s in %s and delete_bcl=%s", run_num, tarbasedir, delete_bcl)
                else:
                    create_run_tar(db, run_num, tarbasedir, delete_bcl)
                trigger = 1
                
        elif record['raw-delete'].get('tar'):
            res = check_tar_status_and_delete(db, record, args.min_tar_age, dryrun=args.dryrun)
            if res:
                trigger = 1
        if args.break_after_first and trigger == 1:
            LOGGER.info("Stopping after first run")
            break

if __name__ == "__main__":
    main()
