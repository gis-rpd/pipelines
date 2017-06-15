#!/usr/bin/env python3
"""Crawl DB for started downstream runs and resp. output folders for
flag files indicating completion, upon which DB needs update

"""


#--- standard library imports
#
import sys
import os
import argparse
import logging
import subprocess

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from mongodb import mongodb_conn
from pipelines import generate_window, is_production_user

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

def runs_from_db(testing=True, win=34):
    """Get the runs from pipeline_run collections"""
    connection = mongodb_conn(testing)
    if connection is None:
        sys.exit(1)
    db = connection.gisds.pipeline_runs
    epoch_present, epoch_back = generate_window(win)
    results = db.find({"run.status" : "STARTED",
        "ctime": {"$gt": epoch_back, "$lt": epoch_present}})
    logger.info("Found %d runs for last %s days", results.count(), win)
    for record in results:
        logger.debug("record: %s", record)
        if not record.get('outdir'):
            logger.critical("outdir is missing for DB-id %s", record['_id'])
            continue
        run_records = (record['_id'], record['outdir'])
        yield run_records

def main():
    """main function
    """
    downstream_logger_script = os.path.abspath(os.path.join(
        os.path.dirname(sys.argv[0]), "downstream_logger.py"))
    assert os.path.exists(downstream_logger_script)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-t', "--testing", action='store_true',
                        help="Use MongoDB test server")
    default = 64
    parser.add_argument('-w', '--win', type=int, default=default,
                        help="Number of days to look back (default {})".format(default))
    parser.add_argument('-n', "--dry-run", action='store_true',
                        help="Dry run")
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
    # generator to get the run records list from pipeline_run collection!
    run_records = runs_from_db(args.testing, args.win)
    for _id, outdir in run_records:
        downstream_logger_script_cmd = [downstream_logger_script,
                                    '-d', str(_id), '-o', outdir, '-m', 'check']
        if args.testing:
            downstream_logger_script_cmd.append("-t")
        if args.dry_run:
            logger.info("Skipping dryrun option %s", outdir)
            continue
        try:
            _ = subprocess.check_output(downstream_logger_script_cmd, \
                stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            logger.fatal("The following command failed with return code %s: %s",
                         e.returncode, ' '.join(downstream_logger_script_cmd))
            logger.fatal("Output: %s", e.output.decode())
            break

if __name__ == "__main__":
    main()

