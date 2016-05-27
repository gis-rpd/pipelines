#!/usr/bin/env python3
"""Crawl DB for started bcl2fastq runs and resp. output folders for
flag files indicating completion, upon which DB needs update

"""


#--- standard library imports
#
import sys
import os
import argparse
import logging
import subprocess
from datetime import datetime

#--- third-party imports
#
import yaml
## only dump() and following do not automatically create aliases
yaml.Dumper.ignore_aliases = lambda *args: True

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from mongo_status import mongodb_conn
from pipelines import generate_window, timestamp_from_string
from bcl2fastq import PIPELINE_CONFIG_FILE


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


DBUPDATE_TRIGGER_FILE_FMT = "TRIGGER.DBUPDATE.{num}"
# up to DBUPDATE_TRIGGER_FILE_MAXNUM trigger files allowed
DBUPDATE_TRIGGER_FILE_MAXNUM = 9


BASEDIR = os.path.dirname(sys.argv[0])


# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)



class MongoUpdate(object):
    """Helper class for mongodb updates
    """
    
    def __init__(self, run_num, analysis_id, testing=False, dryrun=False):
        self.run_num = run_num
        self.analysis_id = analysis_id
        self.testing = testing
        self.dryrun = dryrun

        mongo_status_script = os.path.abspath(os.path.join(
            os.path.dirname(sys.argv[0]), "mongo_status.py"))
        assert os.path.exists(mongo_status_script), (
            "Missing {}".format(mongo_status_script))
        self.mongo_status_script = mongo_status_script

        mongo_status_per_mux_script = os.path.abspath(os.path.join(
            os.path.dirname(sys.argv[0]), "mongo_status_per_mux.py"))
        assert os.path.exists(mongo_status_per_mux_script), (
            "Missing {}".format(mongo_status_per_mux_script))
        self.mongo_status_per_mux_script = mongo_status_per_mux_script


    def update_run(self, status, outdir):
        """update status for run
        """
        logger.info("Updating status for run %s analysis %s to %s",
                    self.analysis_id, self.run_num, status)
        cmd = [self.mongo_status_script, '-r', self.run_num,
               '-a', self.analysis_id, '-s', status, '-o', outdir]

        if self.testing:
            cmd.append("-t")
        if self.dryrun:
            cmd.append("--dry-run")

        try:
            _ = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            logger.critical("The following command failed with return code %s: %s",
                            e.returncode, ' '.join(cmd))
            logger.critical("Output: %s", e.output.decode())
            return False
        else:
            return True


    def update_mux(self, status, mux_id, mux_dir):
        """update status for mux
        """
        logger.info("Updating status for mux %s of analysis %s in run %s to %s",
                    mux_id, self.analysis_id, self.run_num, status)
        cmd = [self.mongo_status_per_mux_script, '-r', self.run_num,
               '-a', self.analysis_id, '-s', status,
               '-i', mux_id, '-d', mux_dir]

        if self.testing:
            cmd.append("-t")
        if self.dryrun:
            cmd.append("--dry-run")

        try:
            _ = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            logger.critical("The following command failed with return code %s: %s",
                            e.returncode, ' '.join(cmd))
            logger.critical("Output: %s", e.output.decode())
            return False
        else:
            return True


def get_outdirs_from_db(testing=True, win=14):
    """FIXME:add-doc"""
    connection = mongodb_conn(testing)
    if connection is None:
        sys.exit(1)

    db = connection.gisds.runcomplete
    epoch_present, epoch_back = generate_window(win)

    results = db.find({"analysis": {"$exists": 1},
                       "timestamp": {"$gt": epoch_back, "$lt": epoch_present}})
    # results is a pymongo.cursor.Cursor which works like an iterator i.e. dont use len()
    logger.info("Found %d runs for last %s days", results.count(), win)
    for record in results:
        logger.debug("record: %s", record)
        #run_number = record['run']
        # we might have several analysis runs:
        for analysis in record['analysis']:
            yield analysis["out_dir"]


def mux_dir_complete(muxdir, completed_after=None):
    """Will check whether necessary flag files for muxdir exist. Will return false if one is missing.
    If completed_after is given or if both exist, but none is newer than completed_after.
    """

    if not os.path.exists(muxdir):
        logger.error("Directory %s doesn't exist", muxdir)
        return False
    at_least_one_newer = False
    for f in ['bcl2fastq.SUCCESS', 'fastqc.SUCCESS']:
        f = os.path.join(muxdir, f)
        if not os.path.exists(f):
            logger.debug("mux dir %s incomplete: %s is missing", muxdir, f)
            return False
        if completed_after:
            if datetime.fromtimestamp(os.path.getmtime(f)) > completed_after:
                at_least_one_newer = True
    if completed_after and not at_least_one_newer:
        return False
    return True


def main():
    """main function
    """
    # FIXME ugly and duplicated in bcl2fastq.py
    mongo_status_per_mux_script = os.path.abspath(os.path.join(
        os.path.dirname(sys.argv[0]), "mongo_status_per_mux.py"))
    assert os.path.exists(mongo_status_per_mux_script)
    assert os.path.exists(mongo_status_per_mux_script)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-t', "--testing", action='store_true',
                        help="Use MongoDB test server")
    default = 14
    parser.add_argument('-w', '--win', type=int, default=default,
                        help="Number of days to look back (default {})".format(default))
    parser.add_argument('--outdirs', nargs="*",
                        help="Ignore DB entries and go through this list"
                        " of directories (DEBUGGING)")
    parser.add_argument('-n', '--dry-run', action='store_true')
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

    if args.outdirs:
        logger.warning("Using manually defined outdirs")
        outdirs = args.outdirs
    else:
        # generator!
        outdirs = get_outdirs_from_db(args.testing, args.win)

    num_triggers = 0
    for outdir in outdirs:

        # load mux info from config instead of relying on filesystem
        #
        logger.debug("Loading config for %s", outdir)
        config_file = os.path.join(outdir, PIPELINE_CONFIG_FILE)
        if not os.path.exists(config_file):
            logger.critical("Missing config file %s. Skipping this directory", config_file)
            continue
        with open(config_file) as fh:
            cfg = yaml.safe_load(fh)
        muxes = dict([(x['mux_id'], x['mux_dir']) for x in cfg['units'].values()])

        # look for trigger files. use their info for update and delete
        #
        for i in range(DBUPDATE_TRIGGER_FILE_MAXNUM+1):
            # multiple trigger files per directory allowed (but rare)
            trigger_file = os.path.join(outdir, DBUPDATE_TRIGGER_FILE_FMT.format(num=i))
            if not os.path.exists(trigger_file):
                continue

            logger.debug("Processing trigger file %s", trigger_file)
            num_triggers += 1
            with open(trigger_file) as fh:
                update_info = yaml.safe_load(fh)

            mongo_updater = MongoUpdate(update_info['run_num'],
                                        update_info['analysis_id'],
                                        args.testing, args.dry_run)

            res = mongo_updater.update_run(update_info['status'], outdir)
            if not res:
                # don't delete trigger. don't processe muxes. try again later
                logger.critical("Skipping this analysis (%s) for run %s", update_info['analysis_id'], update_info['run_num'])
                continue

            # update per MUX
            #
            keep_trigger = False
            for mux_id, mux_dir_base in muxes.items():
                mux_dir = os.path.join(outdir, "out", mux_dir_base)# ugly
                if mux_dir_complete(mux_dir):
                    # skip the ones completed before
                    completed_after = timestamp_from_string(update_info['analysis_id'])
                    if not mux_dir_complete(mux_dir, completed_after=completed_after):
                        continue
                    status = 'SUCCESS'
                else:
                    status = 'FAILED'

                res = mongo_updater.update_mux(status, mux_id, mux_dir_base)
                if not res:
                    # don't delete trigger. try again later
                    logger.critical("Skipping rest of analysis %s for run %s", update_info['analysis_id'], update_info['run_num'])
                    keep_trigger = True
                    break
                    
            if not args.dry_run and not keep_trigger:
                os.unlink(trigger_file)

    logger.info("%s dirs with triggers", num_triggers)


if __name__ == "__main__":
    main()
