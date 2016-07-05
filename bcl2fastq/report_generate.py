#!/usr/bin/env python3
"""Generate report for the bcl2fastq pipeline
"""
# standard library imports
import logging
import sys
import os
import argparse
import collections
import datetime
import dateutil.relativedelta

#--- third party imports
# /

#--- project specific imports
#
from mongo_status import mongodb_conn
from pipelines import generate_window, isoformat_to_epoch_time
from pipelines import send_mail

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


def main():
    """main function
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-t', "--testing", action='store_true',
                        help="Use MongoDB test server")
    parser.add_argument('-n', "--no-mail", action='store_true',
                        help="Don't mail. Just print to console")
    default = 14
    parser.add_argument('-w', '--win', type=int, default=default,
                        help="Number of days to look back (default {})".format(default))
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
    connection = mongodb_conn(args.testing)
    if connection is None:
        sys.exit(1)
    db = connection.gisds.runcomplete
    epoch_present, epoch_back = generate_window(args.win)
    results = db.find({"timestamp": {"$gt": epoch_back, "$lt": epoch_present}})
    runs = {}
    extra_text = ""
    for record in results:
        run_number = record['run']
        timestamp = record['timestamp']
        runs[timestamp] = run_number
    od = collections.OrderedDict(sorted(runs.items()))
    logger.info("Found %s runs", results.count())
    extra_text = "Found {} runs. \n".format(results.count())
    for _, v in od.items():# v is run
        results = db.find({"run": v})
        for record in results:
            if not 'analysis' in record:
                continue
            last_analysis = record['analysis'][-1]
            status = last_analysis.get("Status")
            if not status:
                continue

            if status == 'SUCCESS':
                if last_analysis.get("per_mux_status"):
                    mux = last_analysis.get("per_mux_status")
                    for d in mux:
                        if d is None:
                            logger.warning("Skipping empty per_mux_status for run %s. Needs fix in DB", v)
                            continue
                        if d.get('Status') == "SUCCESS":# FIXME what if key is missing?
                            mux_id = d['mux_id']

                            stats_submission = d['StatsSubmission']
                            if stats_submission == "FAILED":
                                extra_text += "StatsSubmission for mux_id {} from run {} " \
                                    "has FAILED and out_dir is {} \n" \
                                     .format(mux_id, v, last_analysis.get("out_dir"))
                                extra_text += "\n"

                            archive_submission = d['ArchiveSubmission']
                            if archive_submission == "FAILED":
                                extra_text += "ArchiveSubmission for mux_id {} from run {} " \
                                    "has FAILED and out_dir is {} \n" \
                                    .format(mux_id, v, last_analysis.get("out_dir"))
                                extra_text += "\n"

            elif status == 'FAILED':
                extra_text += "Analysis for run {} has failed. \n".format(v)
                extra_text += "Analysis_id is {} and out_dir is {} \n" \
                    .format(last_analysis.get("analysis_id"), \
                    last_analysis.get("out_dir"))
                extra_text += "\n"
                extra_text += "---------------------------------------------------\n"
                logger.info("Analysis for run %s has failed ", v)

            elif status == 'STARTED':
                analysis_id = last_analysis.get("analysis_id")
                analysis_epoch_time = isoformat_to_epoch_time(analysis_id+"+08:00")
                run_completion_time = timestamp/1000
                dt1 = datetime.datetime.fromtimestamp(run_completion_time)
                dt2 = datetime.datetime.fromtimestamp(analysis_epoch_time)
                rd = dateutil.relativedelta.relativedelta(dt1, dt2)
                if rd.days > 3:
                    extra_text += "Analysis for run {} was started {} days ago. "\
                        "Please check. \n".format(v, rd.days)
                    extra_text += "Analysis_id is {} and out_dir is {} \n" \
                        .format(last_analysis.get("analysis_id"), \
                        last_analysis.get("out_dir"))
                    extra_text += "\n"
                    extra_text += "---------------------------------------------------\n"

    extra_text += "Report generation is completed"
    subject = "Report generation for bcl2fastq"
    if args.testing:
        subject = "Testing:" + subject
    if args.no_mail:
        print("Skipping sending of email with subject '{}' and following body:".format(subject))
        print(extra_text)
    else:
        send_mail(subject, extra_text)
    logger.info("Report generation is completed")


if __name__ == "__main__":
    logger.info("Report generation starting")
    main()
