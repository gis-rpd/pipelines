#!/usr/bin/env python3
"""
Keep an eye on production jobs etc and issue warnings if predefined
thresholds are exceeded

"""

# standard library imports
import datetime
import os
#from pprint import PrettyPrinter
from subprocess import CalledProcessError, check_output, getoutput
import sys

# third party imports
# /

# project specific imports
#
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from pipelines import generate_window
from mongodb import mongodb_conn


__author__ = "LIEW Jun Xian"
__email__ = "liewjx@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# max jobs in qw
MAX_QW = 1000
# max jobs in Eqw
MAX_EQW = 0
# max total jobs
MAX_ALL = 10000
# max age in days for running jobs
MAX_AGE = 5
# max percent usage of predefined FSs
MAX_DF = 90
FS_TO_CHECK = ["/mnt/seq", "/mnt/projects/rpd", "/mnt/projects/userrig"]
# max age in days for timestamp window of interest
MAX_WINDOW = 7
# max age in days for started runs
MAX_RUN = 3


def check_qstat():
    """
    run several checks on qstat
    warnings returned as strings/lines
    """
    qstat_cmd = ["qstat", "-u", "userrig"]
    warnings = ""
    try:
        _ = check_output(qstat_cmd)
    except CalledProcessError:
        warnings += ("[qstat fail]")
        return warnings

    count_qw = 0
    count_eqw = 0
    count_all = 0
    for line in check_output(qstat_cmd).splitlines():
        if str.isdigit(str(line.split()[0], "utf-8")):
            count_all += 1
            status = str(line.split()[4], "utf-8")
            if status == "qw":
                count_qw += 1
            if status == "Eqw":
                count_eqw += 1
            if status == 'r':
                submit = datetime.datetime.strptime(str(line.split()[5], "utf-8"), "%m/%d/%Y")
                if ((datetime.date.today() - datetime.date(submit.year, submit.month, \
                    submit.day)).days) > MAX_AGE:
                    warnings += ("[age > " + str(MAX_AGE) + " days]:\t" + "job-ID " + \
                        str(line.split()[0], "utf-8") + "\n")
    if count_qw > MAX_QW:
        warnings += ("[qw > " + str(MAX_QW) + " jobs]:\t" + str(count_qw) + "\n")
    if count_eqw > MAX_EQW:
        warnings += ("[Eqw > " + str(MAX_EQW) + " jobs]:\t" + str(count_eqw) + "\n")
    if count_all > MAX_ALL:
        warnings += ("[all > " + str(MAX_ALL) + " jobs]:\t" + str(count_all) + "\n")
    return warnings


def check_df(fs_to_check):
    """
    check file systems usage
    warnings returned as strings/lines
    """
    warnings = ""
    for filesys in fs_to_check:
        result = []
        for line in check_output(["df", "-h", filesys]).splitlines():
            result.append(line.split())
        if int(result[2][3][:-1]) > MAX_DF:
            warnings += ("[Use% > " + str(MAX_DF) + "%]:\t" + dir + "\n")
    return warnings


def check_mongo():
    """
    Instantiates MongoDB database object
    For Test Server, testing == True
    For Production Server, testing == False
    """
    warnings = ""
    epoch_present, epoch_window = generate_window(MAX_WINDOW)
    epoch_present, epoch_started = generate_window(MAX_RUN)
    del epoch_present

    query = {}
    query["timestamp"] = {"$gte": epoch_window, "$lte": epoch_started}
    query["analysis.Status"] = "STARTED"
    mongo = mongodb_conn(False).gisds.runcomplete.find(query)
    count_warnings = 0
    for record in mongo:
#        PrettyPrinter(indent=2).pprint(record)
        if record["analysis"][-1]["Status"] != "SUCCESS":
            warnings += ("[started >= " + str(MAX_RUN) + " days]:\t" + str(record["run"]) + "\n")
            count_warnings += 1
    if count_warnings > 0:
        warnings += ("[started >= " + str(MAX_RUN) + " days]:\t" + str(count_warnings) + "\n\n")

    query = {}
    query["timestamp"] = {"$gte": epoch_window, "$lte": epoch_started}
    query["analysis"] = {"$exists": False}
    mongo = mongodb_conn(False).gisds.runcomplete.find(query)
    count_warnings = 0
    for record in mongo:
#        PrettyPrinter(indent=2).pprint(record)
        warnings += ("[no analysis >= " + str(MAX_RUN) + " days]:\t" + str(record["run"]) + "\n")
        count_warnings += 1
    if count_warnings > 0:
        warnings += ("[no analysis >= " + str(MAX_RUN) + " days]:\t" + str(count_warnings) + "\n\n")

    return warnings


def send_email(email, subject, message):
    """
    Send alert email
    """
    getoutput("echo '" + message + "' | mail -s '" + subject + "' " + email)


def main():
    """
    Main function
    """
    warnings = check_qstat()
    warnings += check_df(FS_TO_CHECK)
    warnings += check_mongo()
    if len(warnings):
        print(warnings)
#        send_email("rpd@gis.a-star.edu.sg", "[RPD] Production Warnings", warnings)

if __name__ == "__main__":
    main()
