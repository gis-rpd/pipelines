#!/usr/bin/env python3
"""Mongo status update for bcl2fastq QC checks (Demultiplex summary)
"""

# standard library imports
import logging
import sys
import os
import argparse
import getpass
import subprocess

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from pipelines import generate_window
from mongodb import mongodb_conn

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
    bcl2fastq_qc_script = os.path.abspath(os.path.join(
        os.path.dirname(sys.argv[0]), "bcl2fastq_qc.py"))
    assert os.path.exists(bcl2fastq_qc_script)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-t', "--testing", action='store_true',
                        help="Use MongoDB test server")
    default = 14
    parser.add_argument('-w', '--win', type=int, default=default,
                        help="Number of days to look back (default {})".format(default))
    parser.add_argument('-n', "--dry-run", action='store_true',
                        help="Dry run")
    parser.add_argument('--no-mail', action='store_true',
                        help="Don't send email on detected failures")
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
    user_name = getpass.getuser()
    if user_name != "userrig":
        logger.warning("Not a production user. Skipping sending of emails")
        sys.exit(0)
    connection = mongodb_conn(args.testing)
    if connection is None:
        sys.exit(1)
    db = connection.gisds.runcomplete
    epoch_present, epoch_back = generate_window(args.win)
    results = db.find({"analysis.Status": "SUCCESS", "analysis.QC_status" : {"$exists": 0},
                       "timestamp": {"$gt": epoch_back, "$lt": epoch_present}})
    logger.info("Found %s runs", results.count())
    for record in results:
        run_number = record['run']
        analysis = record['analysis']
        #for analysis in record['analysis']:
        for (analysis_count, analysis) in enumerate(record['analysis']):
            out_dir = analysis["out_dir"]
            analysis_id = analysis['analysis_id']
            status = analysis['Status']
            #Check if bcl2Fastq is completed successfully
            if analysis['Status'] != "SUCCESS":
                logger.info("Analysis is not completed successfully under %s", out_dir)
                continue
            if not os.path.exists(out_dir):
                logger.critical("Following directory listed in DB doesn't exist: %s", out_dir)
                continue
            if args.testing:
                bcl2fastq_qc_out = os.path.join(out_dir, "bcl2fastq_qc.test.txt")
            else:
                bcl2fastq_qc_out = os.path.join(out_dir, "bcl2fastq_qc.txt")
            if os.path.exists(bcl2fastq_qc_out):
                logger.critical("Refusing to overwrite existing file %s. Skipping QC check", bcl2fastq_qc_out)
                continue
                
            bcl2fastq_qc_cmd = [bcl2fastq_qc_script, '-d', out_dir]
            if args.no_mail:
                bcl2fastq_qc_cmd.append("--no-mail")
            if args.dry_run:
                logger.warning("Skipped following run: %s", out_dir)
                continue
            try:
                QC_status = "analysis.{}.QC_status".format(analysis_count)
                status = subprocess.check_output(bcl2fastq_qc_cmd, stderr=subprocess.STDOUT)
                if "QC_FAILED" in str(status):
                    db.update({"run": run_number, 'analysis.analysis_id' : analysis_id},
                        {"$set": {QC_status: "FAILED"}})
                    logger.info("Demux QC failed for run: %s", run_number)
                else:
                    db.update({"run": run_number, 'analysis.analysis_id' : analysis_id},
                        {"$set": {QC_status: "SUCCESS"}})
                    logger.info("Demux QC SUCCESS for run: %s", run_number)
                with open(bcl2fastq_qc_out, 'w') as fh:
                    fh.write(status.decode())
            except subprocess.CalledProcessError as e:
                logger.fatal("The following command failed with return code %s: %s",
                             e.returncode, ' '.join(bcl2fastq_qc_cmd))
                logger.fatal("Output: %s", e.output.decode())
                logger.fatal("Exiting")
    connection.close()
if __name__ == "__main__":
    logger.info("Demultiplexing QC status")
    main()
