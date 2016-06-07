#!/usr/bin/env python3
"""STATs and SRA update for the bcl2fastq pipeline
""""""Send email to NGSP and library submitters once bcl2fastq pipeline is completed
"""

# standard library imports
import logging
import sys
import os
import argparse
import getpass
import subprocess
import yaml

#--- third party imports
# WARN: need in conda root and snakemake env
import pymongo

#--- project specific imports
#
from mongo_status import mongodb_conn
from pipelines import generate_window, send_report_mail
from pipelines import is_devel_version


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

def update_mongodb_email(db, run_number, analysis_id, email_sent, Status):
    try:
        db.update({"run": run_number, 'analysis.analysis_id' : analysis_id},
            {"$set": {
                email_sent: Status,
            }})
    except pymongo.errors.OperationFailure:
        logger.fatal("MongoDB OperationFailure")
        sys.exit(0)

def outpath_url(out_path):
    if out_path.startswith("/mnt/projects/userrig/solexa/"):
        return out_path.replace("/mnt/projects/userrig/solexa/", \
            "http://qlap33.gis.a-star.edu.sg/userrig/runs/solexaProjects/")
    else:
        #raise ValueError(out_path)
        return out_path

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

    if is_devel_version():
        ngsp_mail = 'veeravallil'
    else:
        ngsp_mail = 'ngsp@mailman.gis.a-star.edu.sg'

    if args.testing:
        mail_test = 'veeravallil'

    for record in results:
        run_number = record['run']
        print(run_number)
        for (analysis_count, analysis) in enumerate(record['analysis']):
            analysis_id = analysis['analysis_id']
            per_mux_status = analysis.get("per_mux_status", None)
            if per_mux_status is None:
                continue
            for (mux_count, mux_status) in enumerate(per_mux_status):
                if args.dry_run:
                    logger.warn("Skipping analysis %s run %s MUX %s"
                                " with email_sent %s",
                                analysis_id, run_number, mux_status['mux_id'],
                                mux_status.get('email_sent', None))
                    continue
                email_sent = "analysis.{}.per_mux_status.{}.email_sent".format(
                        analysis_count, mux_count)
                mux_id = mux_status['mux_id']
                out_dir = analysis['out_dir']
                if mux_status.get('Status', None) == "FAILED" and \
                    mux_status.get('email_sent', None) == False:
                    logger.info("MUX %s from %s is not SUCCESS. ",
                                mux_status['mux_id'], run_number)
                    body = "Analysis for {} from {} has failed. Please check the logs under {}" \
                        .format(mux_id, run_number, out_dir+"/logs")
                    #Send email to NGSP and update mongoDB
                    if not args.testing:
                        send_report_mail('bcl2fastq Job for run', 'bcl2fastq Job: '+mux_id, \
                            body, ngsp_mail)
                    else:
                        send_report_mail('bcl2fastq Job for run', 'bcl2fastq Job (T): '+mux_id, \
                            body, mail_test)
                    update_mongodb_email(db, run_number, analysis_id, email_sent, True)
                    continue
                # Send email
                #
                if mux_status.get('Status', None) == "SUCCESS" and mux_status.get('email_sent', \
                    None) == False:
                    out_path = os.path.join(out_dir + '/out/' + mux_status.get('mux_dir') + \
                        '/html/index.html')
                    out = outpath_url(out_path)
                    body = "Analysis for {} from {} is successfully completed. Please check the" \
                        "output under {}".format(mux_id, run_number, out)
                    confinfo = os.path.join(out_dir + '/conf.yaml')
                    #print(body)
                    if not os.path.exists(confinfo):
                        logger.fatal("conf info '%s' does not exist under Run directory.\n" \
                            % (confinfo))
                        sys.exit(1)
                    with open(confinfo) as fh_cfg:
                        yaml_data = yaml.safe_load(fh_cfg)
                        assert "units" in yaml_data
                        for k, v in yaml_data["units"].items():
                            if k == "Project_{}".format(mux_id):
                                requestor = v.get('requestor', None)
                                if not args.testing:
                                    if requestor is not None:
                                        #send email to NGSP and requestor
                                        #FIXME mail_test should be changed to requestor
                                        send_report_mail('bcl2fastq Job', 'bcl2fastq Job: '+mux_id,\
                                            body, ngsp_mail)
                                        update_mongodb_email(db, run_number, analysis_id, \
                                            email_sent, True)
                                        print("email to requestor {}".format(requestor))
                                        send_report_mail('bcl2fastq Job', 'bcl2fastq Job: '+mux_id,\
                                            body, mail_test)
                                    else:
                                        #Send email to NGSP
                                        send_report_mail('bcl2fastq Job for run', 'bcl2fastq Job: '\
                                            +mux_id, body, ngsp_mail)
                                        update_mongodb_email(db, run_number, analysis_id, \
                                            email_sent, True)
                                else:
                                    send_report_mail('bcl2fastq Job for run', 'bcl2fastq Job(T) : '\
                                        +mux_id, body, mail_test)
                                    update_mongodb_email(db, run_number, analysis_id, \
                                        email_sent, True)
                num_triggers += 1
    # close the connection to MongoDB
    connection.close()
    logger.info("%s dirs with triggers", num_triggers)


if __name__ == "__main__":
    logger.info("Send email to Users and NGSP")
    main()
