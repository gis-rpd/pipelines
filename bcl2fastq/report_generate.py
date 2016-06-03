#!/usr/bin/env python3
"""Generate report for the bcl2fastq pipeline
"""
# standard library imports
import logging
import sys
import os
import argparse
import getpass
import collections
import datetime
import dateutil.relativedelta

#--- third party imports
# WARN: need in conda root and snakemake env
import pymongo

#--- project specific imports
#
from mongo_status import mongodb_conn
from pipelines import generate_window, isoformat_to_epoch_time
from pipelines import send_report_mail

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

# first level key must match output of get_site()
CONMAP = {
    'gis': {
        'test': "qlap33.gis.a-star.edu.sg:27017",
        'production': "qldb01.gis.a-star.edu.sg:27017,qlap37.gis.a-star.edu.sg:27017,qlap38.gis.a-star.edu.sg:27017,qlap39.gis.a-star.edu.sg:27017"
        },
    'nscc': {
        # using reverse proxy @LMN
        'test': "192.168.190.1:27020",
        'production': "192.168.190.1:27016,192.168.190.1:27017,192.168.190.1:27018,192.168.190.1:27019"
        }
    }

def usage():
    """print usage info"""
    sys.stderr.write("useage: {} [-1]".format(
        os.path.basename(sys.argv[0])))
def main():
    """main function
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-t', "--testing", action='store_true',
                        help="Use MongoDB test server")
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
    print(epoch_present, epoch_back)
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
    for k, v in od.items():
        results = db.find({"run": v})
        for record in results:
            if 'analysis' in record and 'Status' in record['analysis'][-1]:
                Status = record['analysis'][-1].get("Status")
                if Status == 'SUCCESS':
                    if record['analysis'][-1].get("per_mux_status"):
                        mux = record['analysis'][-1].get("per_mux_status")
                        for d in mux:
                            if d['Status'] and (d['Status']) == "SUCCESS":
                                mux_id = d['mux_id']
                                StatsSubmission = d['StatsSubmission']
                                ArchiveSubmission = d['ArchiveSubmission']
                                if StatsSubmission == "FAILED":
                                    extra_text += "StatsSubmission for mux_id {} from Run {} " \
                                        "has FAILED and out_dir is {} \n" \
                                         .format(mux_id, v, record['analysis'][-1].get("out_dir"))
                                    extra_text += "\n"
                                if ArchiveSubmission == "FAILED":
                                    extra_text += "ArchiveSubmission for mux_id {} from Run {} " \
                                        "has FAILED and out_dir is {} \n" \
                                        .format(mux_id, v, record['analysis'][-1].get("out_dir"))
                                    extra_text += "\n"
                elif Status == 'FAILED':
                    extra_text += "Analysis for Run {} has faild. \n".format(v)
                    extra_text += "Analysis_id is {} and out_dir is {} \n" \
                        .format(record['analysis'][-1].get("analysis_id"), \
                        record['analysis'][-1].get("out_dir"))
                    extra_text += "\n"
                    extra_text += "---------------------------------------------------\n"
                    logger.info("Analysis for Run %s has faild ", v)
                elif Status == 'STARTED':
                    analysis_id = record['analysis'][-1].get("analysis_id")
                    analysis_epoch_time = isoformat_to_epoch_time(analysis_id+"+08:00")
                    run_completion_time = timestamp/1000
                    dt1 = datetime.datetime.fromtimestamp(run_completion_time)
                    dt2 = datetime.datetime.fromtimestamp(analysis_epoch_time)
                    rd = dateutil.relativedelta.relativedelta(dt1, dt2)
                    if rd.days > 3:
                        extra_text += "Analysis for Run {} has been started {} days ago. "\
                            "Please check. \n".format(v, rd.days)
                        extra_text += "Analysis_id is {} and out_dir is {} \n" \
                            .format(record['analysis'][-1].get("analysis_id"), \
                            record['analysis'][-1].get("out_dir"))
                        extra_text += "\n"
                        extra_text += "---------------------------------------------------\n" 
    extra_text += "Report generation is completed"
    send_report_mail('Report generation for bcl2fastq', 'Report generation for bcl2fastq', extra_text)
    print(extra_text)
    logger.info("Report generation is completed ")
if __name__ == "__main__":
    logger.info("Report generation starting")
    main()