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
import glob

#--- third-party imports
#
import yaml
## only dump() and following do not automatically create aliases
yaml.Dumper.ignore_aliases = lambda *args: True

#--- project specific imports
#
#from pipelines import get_pipeline_version, get_site, get_rpd_vars
#from pipelines import write_dk_init, write_snakemake_init, write_snakemake_env
#from pipelines import write_cluster_config, generate_timestamp
#from pipelines import get_machine_run_flowcell_id, is_devel_version
#from pipelines import email_for_user
#from generate_bcl2fastq_cfg import MUXINFO_CFG, SAMPLESHEET_CSV, USEBASES_CFG, MuxUnit
from mongo_status import mongodb_conn
from pipelines import generate_window



__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


DBUPDATE_TRIGGER_FILE = "TRIGGER.DBUPDATE"


BASEDIR = os.path.dirname(sys.argv[0])


# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)



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
    logger.info("Found {} runs for last {} days".format(results.count(), win))
    for record in results:
        logger.debug("record: {}".format(record))
        #run_number = record['run']
        # we might have several analysis runs:
        for analysis in record['analysis']:
            if analysis.get("Status", None) == "SUCCESS":#STARTED FIXME
                yield analysis["out_dir"]


def mux_dir_complete(muxdir):
    for x in ['bcl2fastq.SUCCESS', 'fastqc.SUCCESS']:
        if not os.path.exists(os.path.join(muxdir, x)):
            return False
    return True


def main():
    """main function
    """
    # FIXME ugly and duplicated in bcl2fastq.py
    mongo_status_script = os.path.abspath(os.path.join(
        os.path.dirname(sys.argv[0]), "mongo_status.py"))
    assert os.path.exists(mongo_status_script)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-t', "--testing", action='store_true',
                        help="Use MongoDB test server")
    default = 14
    parser.add_argument('-w', '--win', type=int, default=default,
                        help="Number of days to look back (default {})".format(default))
    parser.add_argument('--outdirs', nargs="*",
                        help="Ignore DB entries and go through this list of directories (DEBUGGING)")
    parser.add_argument('-n', '--no-run', action='store_true')
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
        logger.debug("Scanning {}".format(outdir))
        trigger_file = os.path.join(outdir, DBUPDATE_TRIGGER_FILE)
        if not os.path.exists(trigger_file):
            continue
        num_triggers += 1
        with open(trigger_file) as fh:
            update_info = yaml.safe_load(fh)

            # update status for run
            #
            cmd = [mongo_status_script, '-r', update_info['run_num'],
                   '-s', update_info['status'], '-o', outdir,
                   '-a', update_info['analysis_id']]
            if args.testing:
                cmd.append("-t")

            if args.no_run:
                logger.warning("Dry run. Skipping execution of: {}".format(' '.join(cmd)))
            try:
                _ = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                logger.fatal("The following command failed with return code {}: {}".format(
                    e.returncode, ' '.join(cmd)))
                logger.fatal("Output: {}".format(e.output.decode()))
                logger.fatal("Trying to continue")
                continue

            for muxdir in glob.glob(os.path.join(outdir, "out", "Project_*")):
                if mux_dir_complete(muxdir):
                    logger.critical("FIXME Implement: mongo_status_per_mux for {}".format(muxdir))
                    
            os.unlink(trigger_file)
            
    logger.info("{} dirs with triggers".format(num_triggers))

if __name__ == "__main__":
    main()
