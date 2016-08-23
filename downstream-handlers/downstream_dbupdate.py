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
from mongodb import mongodb_conn
from pipelines import generate_window


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

DBUPDATE_TRIGGER_FILE_FMT = "TRIGGER.DBUPDATE.{num}"
# up to DBUPDATE_TRIGGER_FILE_MAXNUM trigger files allowed
DBUPDATE_TRIGGER_FILE_MAXNUM = 9

def runs_from_db(testing=True, win=34):
    """Get the runs from pipeline_run collections"""
    connection = mongodb_conn(testing)
    if connection is None:
        sys.exit(1)
    db = connection.gisds.pipeline_runs
    epoch_present, epoch_back = generate_window(win)
    results = db.find({"runs": {"$exists": True},
                       "ctime": {"$gt": 1470127013000, "$lt": 1470127093000}})
    # results is a pymongo.cursor.Cursor which works like an iterator i.e. dont use len()
    logger.info("Found %d runs for last %s days", results.count(), win)
    for record in results:
        logger.debug("record: %s", record)
        for runs in record['runs']:
            if runs["status"] == "STARTED":
                test = (record['_id'], record['out_dir'], runs['start_time'])
                yield test

def main():
    """main function
    """
    pipeline_status_script = os.path.abspath(os.path.join(
        os.path.dirname(sys.argv[0]), "pipeline_status.py"))
    assert os.path.exists(pipeline_status_script)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-t', "--testing", action='store_true',
                        help="Use MongoDB test server")
    default = 64
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
        outdirs = runs_from_db(args.testing, args.win)
    num_triggers = 0
    for _id, out_dir, start_time in outdirs:
        #Check if trigger file is available
        for i in range(DBUPDATE_TRIGGER_FILE_MAXNUM+1):
            trigger_file = os.path.join(out_dir, DBUPDATE_TRIGGER_FILE_FMT.format(num=i))
            if not os.path.exists(trigger_file):
                continue
            logger.debug("Processing trigger file %s", trigger_file)
            num_triggers += 1
            with open(trigger_file) as fh:
                update_info = yaml.safe_load(fh)
                if (update_info['start_time'] == start_time) and (update_info['DBid'] == str(_id)):
                    #Update the info from Trigger file
                    pipeline_status_script_cmd = [pipeline_status_script,
                        '-r', update_info['DBid'], '-o', out_dir, '-s', update_info['status'],
                        '-st', update_info['start_time']]
                    if args.testing:
                        pipeline_status_script_cmd.append("-t")
                    print(pipeline_status_script_cmd)
                    try:
                        _ = subprocess.check_output(pipeline_status_script_cmd, \
                            stderr=subprocess.STDOUT)
                        os.unlink(trigger_file)
                    except subprocess.CalledProcessError as e:
                        logger.fatal("The following command failed with return code %s: %s",
                                     e.returncode, ' '.join(pipeline_status_script_cmd))
                        logger.fatal("Output: %s", e.output.decode())
                        break

if __name__ == "__main__":
    main()
