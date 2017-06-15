#!/usr/bin/env python3
"""Check ELM run association
"""
# standard library imports
import logging
import sys
import argparse
import os

# project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from mongodb import mongodb_conn
from pipelines import generate_window
from pipelines import is_production_user
from pipelines import is_devel_version
from pipelines import get_machine_run_flowcell_id
from generate_bcl2fastq_cfg import get_rest_data
from pipelines import send_mail

# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)

__author__ = "Lavanya Veeravalli"
__email__ = "veeravallil@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


def runs_from_db(db, mail_to, ccaddr, win=34):
    """Get the runs from pipeline_run collections"""
    epoch_present, epoch_back = generate_window(win)
    results = db.find({"analysis" : {"$exists": False},
                       "timestamp": {"$gt": epoch_back, "$lt": epoch_present}})
    logger.info("Found %d runs for last %s days", results.count(), win)
    mail = False
    subject = "Runs with missing ELM information"
    body = "Dear NGSP, " + "\n"
    body += subject + " for the following runs. Please include in the ELM." + "\n"
    for record in results:
        logger.debug("record: %s", record)
        _, runid, _ = get_machine_run_flowcell_id(record.get('run'))
        rest_data = get_rest_data(runid)
        if not rest_data.get('runId'):
            body += record.get('run')+ "\n"
            mail = True
    if mail:
        send_mail(subject, body, toaddr=mail_to, ccaddr=ccaddr)


def main():
    """main function
    """
    parser = argparse.ArgumentParser(description=__doc__)
    default = 34
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
    db = connection.gisds.runcomplete
    if is_devel_version() or args.testing:
        mail_to = 'veeravallil'# domain added in mail function
        ccaddr = None
    else:
        mail_to = 'GISNGSPlatform@gis.a-star.edu.sg'
        ccaddr = "rpd"
    runs_from_db(db, mail_to, ccaddr, args.win)


if __name__ == "__main__":
    main()
