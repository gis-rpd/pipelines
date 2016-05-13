#!/usr/bin/env python3
"""MongoDB status updates for the bcl2fastq pipeline
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
from pipelines import generate_timestamp, generate_window

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
    logger.info("Database connection established")
    db = connection.gisds.runcomplete
    epoch_present, epoch_back = generate_window(args.win)
    results = db.find({"analysis.Status": "SUCCESS",
                       "timestamp": {"$gt": epoch_back, "$lt": epoch_present}})
    logger.info("Found {} runs".format(results.count()))
    for record in results:
        run_number = record['run']
        analysis = record['analysis']
        count = 0
        for analysis in record['analysis']:
            if analysis.get("per_mux_status"):
                mux = analysis.get("per_mux_status")
                analysis_id = analysis['analysis_id']
                for d in mux:
                    if d['Status']:
                        if (d['Status']) == "SUCCESS":
                            logger.info("Upload SRA & STATs request for {}".format(d['mux_id']))
                            mux_id = d['mux_id']
                            out_dir = analysis['out_dir']
                            StatsSubmission = "analysis.$.per_mux_status.{}.StatsSubmission".format(count)
                            ArchiveSubmission = "analysis.$.per_mux_status.{}.ArchiveSubmission".format(count)
                            if not args.dry_run:
                                # Call STATS upload
                                stats_upload_script_cmd = [stats_upload_script, '-o', out_dir, '-m', mux_id]       
                                if args.testing:
                                    stats_upload_script_cmd.append("-t")
                                logger.info(stats_upload_script_cmd)
                                try:
                                    _ = subprocess.check_output(stats_upload_script_cmd, stderr=subprocess.STDOUT)
                                    StatsSubmission_status = "SUCCESS"
                                except subprocess.CalledProcessError as e:
                                    logger.critical("The following command failed with return code %s: %s",
                                    e.returncode, ' '.join(stats_upload_script_cmd))
                                    logger.critical("Output: %s", e.output.decode())
                                    logger.info("error code", e.output)
                                    StatsSubmission_status = "TODO"
                                # Call FASTQ upload FIXME
                                archive_upload_script_cmd = [archive_upload_script, '-o', out_dir, '-m', mux_id]                                   
                                if args.testing:
                                    archive_upload_script_cmd.append("-t")
                                logger.info(archive_upload_script_cmd)
                                try:    
                                    _ = subprocess.check_output(archive_upload_script_cmd, stderr=subprocess.STDOUT)
                                    ArchiveSubmission_status = "SUCCESS"
                                except subprocess.CalledProcessError as e:
                                    logger.critical("The following command failed with return code %s: %s",
                                    e.returncode, ' '.join(archive_upload_script_cmd))
                                    logger.critical("Output: %s", e.output.decode())
                                    logger.info("error code", e.output)
                                    ArchiveSubmission_status = "TODO"
                                #upDate mongoDB
                                logger.info("MongoDB update for mux {}".format(mux_id))
                                try:
                                    db.update({"run": run_number, 'analysis.analysis_id' : analysis_id},
                                        {"$set": {
                                            StatsSubmission: StatsSubmission_status, 
                                            ArchiveSubmission: ArchiveSubmission_status
                                        }})
                                except pymongo.errors.OperationFailure:
                                    logger.fatal("mongoDB OperationFailure")
                                    sys.exit(0)                             
                        else:
                            logger.info("Mux {} is not successfully completed. Skip SRA and STATS uploading".format(d['mux_id']))
                    count += 1  
    # close the connection to MongoDB
    connection.close()

if __name__ == "__main__":
    logger.info("MongoDB status update starting")
    main()
    logger.info("Successful program exit")
