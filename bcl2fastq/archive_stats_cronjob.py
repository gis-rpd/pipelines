#!/usr/bin/env python3
"""STATs and SRA update for the bcl2fastq pipeline
"""

# standard library imports
import logging
import sys
import os
import argparse
import getpass
import subprocess

#--- third party imports
# WARN: need in conda root and snakemake env
import pymongo

#--- project specific imports
#
from mongo_status import mongodb_conn
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



def main():
    """main function
    """
    stats_upload_script = os.path.abspath(os.path.join(
        os.path.dirname(sys.argv[0]), "bcl_stats_upload.py"))
    assert os.path.exists(stats_upload_script)
    archive_upload_script = os.path.abspath(os.path.join(
        os.path.dirname(sys.argv[0]), "sra_fastq_upload.py"))
    assert os.path.exists(archive_upload_script)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-t', "--testing", action='store_true',
                        help="Use MongoDB test server")
    default = 14
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

    user_name = getpass.getuser()
    if user_name != "userrig":
        logger.warning("Not a production user. Skipping MongoDb update")
        sys.exit(0)

    connection = mongodb_conn(args.testing)
    if connection is None:
        sys.exit(1)
    db = connection.gisds.runcomplete
    epoch_present, epoch_back = generate_window(args.win)
    num_triggers = 0
    results = db.find({"analysis" : {"$exists": True},
                       "timestamp": {"$gt": epoch_back, "$lt": epoch_present}})
    logger.info("Found %s runs", results.count())

    for record in results:
        run_number = record['run']

        for (analysis_count, analysis) in enumerate(record['analysis']):
            analysis_id = analysis['analysis_id']

            per_mux_status = analysis.get("per_mux_status", None)
            if per_mux_status is None:
                continue

            for (mux_count, mux_status) in enumerate(per_mux_status):
                # sanity checks against corrupted DB entries
                if mux_status is None or mux_status.get('mux_id') is None:
                    logger.warning("mux_status is None or incomplete for run %s analysis %s."
                                   " Requires fix in DB. Skipping entry for now.", run_number, analysis_id)
                    continue
                
                if mux_status.get('Status', None) != "SUCCESS":
                    logger.info("MUX %s from %s is not SUCCESS. Skipping SRA and STATS uploading",
                                mux_status['mux_id'], run_number)
                    continue

                mux_id = mux_status['mux_id']
                out_dir = analysis['out_dir']

                if args.dry_run:
                    logger.warning("Skipping analysis %s run %s MUX %s"
                                " with StatsSubmission %s and ArchiveSubmission %s",
                                analysis_id, run_number, mux_status['mux_id'],
                                mux_status.get('StatsSubmission', None),
                                mux_status.get('ArchiveSubmission', None))
                    continue

                # Call STATS upload
                #
                if mux_status.get('StatsSubmission', None) == "TODO":
                    logger.info("Stats upload for %s from %s and analysis_id is %s",
                                mux_id, run_number, analysis_id)
                    StatsSubmission = "analysis.{}.per_mux_status.{}.StatsSubmission".format(
                        analysis_count, mux_count)

                    stats_upload_script_cmd = [stats_upload_script,
                                               '-o', out_dir, '-m', mux_id]
                    if args.testing:
                        stats_upload_script_cmd.append("-t")
                    try:
                        _ = subprocess.check_output(stats_upload_script_cmd, stderr=subprocess.STDOUT)
                        StatsSubmission_status = "SUCCESS"
                    except subprocess.CalledProcessError as e:
                        logger.fatal("The following command failed with return code %s: %s",
                                     e.returncode, ' '.join(stats_upload_script_cmd))
                        logger.fatal("Output: %s", e.output.decode())
                        logger.fatal("Resetting to TODO")
                        StatsSubmission_status = "TODO"
                    try:
                        db.update({"run": run_number, 'analysis.analysis_id' : analysis_id},
                                  {"$set": {
                                      StatsSubmission: StatsSubmission_status,
                                  }})
                    except pymongo.errors.OperationFailure:
                        logger.fatal("MongoDB OperationFailure")
                        sys.exit(0)
                    num_triggers += 1

                # Call FASTQ upload
                #
                if mux_status.get('ArchiveSubmission', None) == "TODO":
                    logger.info("SRA upload for %s from %s and analysis_id is %s",
                                mux_id, run_number, analysis_id)
                    ArchiveSubmission = "analysis.{}.per_mux_status.{}.ArchiveSubmission".format(
                        analysis_count, mux_count)
                    archive_upload_script_cmd = [archive_upload_script,
                                                 '-o', out_dir, '-m', mux_id]
                    if args.testing:
                        archive_upload_script_cmd.append("-t")
                    try:
                        _ = subprocess.check_output(archive_upload_script_cmd, stderr=subprocess.STDOUT)
                        ArchiveSubmission_status = "SUCCESS"
                    except subprocess.CalledProcessError as e:
                        logger.fatal("The following command failed with return code %s: %s",
                                     e.returncode, ' '.join(archive_upload_script_cmd))
                        logger.fatal("Output: %s", e.output.decode())
                        logger.fatal("Resetting to TODO")
                        ArchiveSubmission_status = "TODO"
                    #update mongoDB
                    try:
                        db.update({"run": run_number, 'analysis.analysis_id' : analysis_id},
                                  {"$set": {
                                      ArchiveSubmission: ArchiveSubmission_status
                                  }})
                    except pymongo.errors.OperationFailure:
                        logger.fatal("MongoDB OperationFailure")
                        sys.exit(0)
                    num_triggers += 1

    # close the connection to MongoDB
    connection.close()
    logger.info("%s dirs with triggers", num_triggers)


if __name__ == "__main__":
    logger.info("STATs and SRA status update starting")
    main()
