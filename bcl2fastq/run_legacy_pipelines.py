#!/usr/bin/env python3
"""Cronjob for triggering BWA and RNAseq pipeline
"""
# standard library imports
import logging
import os
import argparse
import subprocess
import sys

# third party imports
# WARN: need in conda root and snakemake env
#import pymongo

# project specific imports
#
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from mongo_status import mongodb_conn
from pipelines import send_status_mail, generate_timestamp, generate_window


__author__ = "Lavanya Veeravalli"
__email__ = "veeravallil@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# log dir relative to outdir
LOG_DIR_REL = "mappping_logs"
# Submission log relative to outdir
SUBMISSIONLOG = os.path.join(LOG_DIR_REL, "mapping_submission.log")
# same as folder name. also used for cluster job names
PIPELINE_NAME = "Mapping"
#CONFIG
CONFIG = "/home/userrig/Solexa/bcl2fastq2-v2.17/"
CONFIG += "generateBCL2FASTQ2.17config.sh"
#BWA mapping pipeline
BWA = "/home/userrig/pipelines/NewBwaMappingPipelineMem/"
BWA += "generateBwa0.7.5aconfigurationV217V2.sh"
#RNA mapping pipeline
RNA = "/home/userrig/pipelines/NewRNAseqTophatCufflinksPipeline/"
RNA += "generateTophatCufflinksconfigurationV217V2.sh"
#ANALYSIS_ID
analysis_id = generate_timestamp()
# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)


def check_break_status(break_after_first):
    if break_after_first:
        logger.warning("Stopping after first sequencing run")
        sys.exit(0)


def main():
    """main function"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-1', "--break-after-first", action='store_true',
                        help="Only process first run returned")
    parser.add_argument('-n', "--dry-run", action='store_true',
                        help="Don't run anything")
    parser.add_argument('-t', "--testing", action='store_true',
                        help="Use MongoDB test-server")
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
    #Check if pipeline scripts are available
    assert os.path.exists(BWA)
    assert os.path.exists(RNA)
    connection = mongodb_conn(args.testing)
    if connection is None:
        sys.exit(1)
    db = connection.gisds.runcomplete
    epoch_present, epoch_back = generate_window(args.win)
    num_triggers = 0
    results = db.find({"analysis.Status": "SUCCESS",
                       "timestamp": {"$gt": epoch_back, "$lt": epoch_present}})
    logger.info("Found %s runs", results.count())
    for record in results:
        run_number = record['run']
        analysis = record['analysis']
        for analysis in record['analysis']:
            out_dir = analysis.get("out_dir")

            #Check if bcl2Fastq is completed successfully
            if 'Status' in analysis and analysis.get("Status") == "SUCCESS":
                if not os.path.exists(out_dir):
                    logger.critical("Following directory listed in DB doesn't exist: %s", out_dir)
                    continue

                #Check if downstream analysis has been started
                if not os.path.exists(os.path.join(out_dir, "config_casava-1.8.2.txt".format())):
                    logger.info("Start the downstream analysis at %s", out_dir)
                    os.makedirs(os.path.join(out_dir, LOG_DIR_REL), exist_ok=True)
                    #generate config file
                    config_cmd = [CONFIG, '-r', run_number]
                    try:
                        f = open(os.path.join(out_dir, "config_casava-1.8.2.txt".format()), "w")
                        _ = subprocess.call(config_cmd, stderr=subprocess.STDOUT, stdout=f)
                    except subprocess.CalledProcessError as e:
                        logger.fatal("The following command failed with return code %s: %s",
                                     e.returncode, ' '.join(config_cmd))
                        logger.fatal("Output: %s", e.output.decode())
                        logger.fatal("Exiting")
                        sys.exit(1)
                    #Generate and Submit BWA and RNAseq mapping pipeline
                    if os.path.exists(os.path.join(out_dir, "samplesheet.csv".format())):
                        dirs = os.path.join(out_dir, "out")
                        cmd = "cd {} && {} -r {} -f {} -s {} -j 0 -p Production -c 5 >> {}".format(dirs, BWA, run_number, out_dir, os.path.join(out_dir, "samplesheet.csv".format()), os.path.join(out_dir, SUBMISSIONLOG))
                        cmd += "&& {} -r {} -f {} -s {} -j 0 -p Production -c 5 >> {}".format(RNA, run_number, out_dir, os.path.join(out_dir, "samplesheet.csv".format()), os.path.join(out_dir, SUBMISSIONLOG))
                        if args.dry_run:
                            logger.warning("Skipped following run: %s", cmd)
                            #Remove config txt
                            os.remove(os.path.join(out_dir, "config_casava-1.8.2.txt".format()))
                            check_break_status(args.break_after_first)
                        else:
                            try:
                                #ananlysisReport into submission log
                                with open(os.path.join(out_dir, SUBMISSIONLOG), 'w') as fh:
                                    fh.write(cmd)
                                _ = subprocess.check_output(cmd, shell=True)
                            except subprocess.CalledProcessError as e:
                                logger.fatal("The following command failed with return code %s: %s",
                                             e.returncode, ' '.join(cmd))
                                logger.fatal("Output: %s", e.output.decode())
                                logger.fatal("Exiting")
                                #send_status_mail
                                send_status_mail(PIPELINE_NAME, False, analysis_id, os.path.join(out_dir, LOG_DIR_REL, "mapping_submission.log"))
                                sys.exit(1)
                            num_triggers += 1
                            check_break_status(args.break_after_first)
                    else:
                        #send_status_mail
                        logger.info("samplesheet.csv missing for %s under %s", run_number, out_dir)
                        send_status_mail(PIPELINE_NAME, False, analysis_id, os.path.abspath(out_dir))
            elif analysis.get("Status") == "FAILED":
                logger.debug("BCL2FASTQ FAILED for %s under %s", run_number, out_dir)
     # close the connection to MongoDB
    connection.close()
    logger.info("%s dirs with triggers", num_triggers)


if __name__ == "__main__":
    main()
