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
import yaml

#--- third party imports
#
import pymongo

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from mongodb import mongodb_conn
from pipelines import generate_window, send_mail
from pipelines import is_devel_version
from pipelines import path_to_url


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


def update_mongodb_email(db, run_number, analysis_id, email_sent, Status):
    try:
        db.update({"run": run_number, 'analysis.analysis_id' : analysis_id},
                  {"$set": {email_sent: Status,}})
    except pymongo.errors.OperationFailure:
        logger.fatal("MongoDB OperationFailure")
        sys.exit(0)


def get_requestor(mux_id, cfg_file):
    with open(cfg_file) as fh_cfg:
        yaml_data = yaml.safe_load(fh_cfg)
    assert "units" in yaml_data
    for k, v in yaml_data["units"].items():
        if k == "Project_{}".format(mux_id):
            requestor = v.get('requestor', None)
            return requestor
    return None


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
        logger.warning("Not a production user. Skipping sending of emails")
        sys.exit(0)

    connection = mongodb_conn(args.testing)
    if connection is None:
        sys.exit(1)
    db = connection.gisds.runcomplete
    epoch_present, epoch_back = generate_window(args.win)
    num_emails = 0
    results = db.find({"analysis" : {"$exists": True},
                       "timestamp": {"$gt": epoch_back, "$lt": epoch_present}})
    logger.info("Found %s runs", results.count())

    if is_devel_version() or args.testing:
        mail_to = 'veeravallil'# domain added in mail function
    else:
        #mail_to = 'ongct1@gis.a-star.edu.sg'
        mail_to = 'GISNGSPlatform@gis.a-star.edu.sg'

    for record in results:
        run_number = record['run']
        #print(run_number)
        for (analysis_count, analysis) in enumerate(record['analysis']):
            analysis_id = analysis['analysis_id']
            per_mux_status = analysis.get("per_mux_status", None)
            if per_mux_status is None:
                continue

            for (mux_count, mux_status) in enumerate(per_mux_status):
                if args.dry_run:
                    logger.warning("Skipping analysis %s run %s MUX %s"
                                   " with email_sent %s",
                                   analysis_id, run_number, mux_status['mux_id'],
                                   mux_status.get('email_sent', None))
                    continue

                if mux_status.get('email_sent', None):
                    continue

                # for all others: send email and update db

                email_sent_query = "analysis.{}.per_mux_status.{}.email_sent".format(
                    analysis_count, mux_count)
                mux_id = mux_status['mux_id']
                out_dir = analysis['out_dir']

                if mux_status.get('Status', None) == "FAILED":
                    logger.info("bcl2fastq for MUX %s from %s failed. ",
                                mux_status['mux_id'], run_number)
                    subject = 'bcl2fastq: ' + mux_id
                    body = "bcl2fastq for {} from {} failed.".format(mux_id, run_number)
                    body += "\n\nPlease check the logs under {}".format(out_dir + "/logs")
                    send_mail(subject, body, mail_to, ccaddr="rpd")
                    num_emails += 1
                    update_mongodb_email(db, run_number, analysis_id, email_sent_query, True)

                elif mux_status.get('Status', None) == "SUCCESS":
                    muxdir = os.path.join(out_dir, 'out', mux_status.get('mux_dir'))
                    summary = path_to_url(os.path.join(muxdir, 'html/index.html'))
                    body = "bcl2fastq for {} from {} successfully completed.".format(
                        mux_id, run_number)
                    body += "\n\nA summary can be found at {}".format(summary)
                    body += "\n\nFastQ files are located in {}".format(muxdir)
                    body += "\n\nData can also be downloaded from GIS-SRA (once archival is complete)"
                    
                    confinfo = os.path.join(out_dir, 'conf.yaml')
                    #print(body)
                    if not os.path.exists(confinfo):
                        logger.fatal("conf info '%s' does not exist"
                                     " under run directory.", confinfo)
                        continue

                    subject = 'bcl2fastq'
                    if args.testing:
                        subject += ' testing'
                    if is_devel_version():
                        subject += ' devel'
                    subject += ': ' + mux_id
                    send_mail(subject, body, mail_to, ccaddr="rpd")# mail_to already set

                    if not args.testing and not is_devel_version():
                        requestor = get_requestor(mux_id, confinfo)
                        if requestor is not None:
                            #requestor = "rpd"
                            #subject += " (instead of requestor)"
                            #send_mail(subject, body, requestor, ccaddr="rpd")
                            send_mail(subject, body, requestor)

                    num_emails += 1
                    update_mongodb_email(db, run_number, analysis_id, email_sent_query, True)


    # close the connection to MongoDB
    connection.close()
    logger.info("%d emails sent", num_emails)


if __name__ == "__main__":
    logger.info("Send email to Users and NGSP")
    main()
