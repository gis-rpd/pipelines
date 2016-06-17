#!/usr/bin/env python3
"""Keep an eye on production jobs etc and issue warnings if predefined
thresholds are exceeded

"""

# standard library imports
import subprocess
import datetime

# third party imports
# /

# project specific imports
# /


__author__ = "LIEW Jun Xian"
__email__ = "liewjx@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# max jobs in qw
THRESHOLD_QW = 1000
# max jobs in Eqw
THRESHOLD_EQW = 0
# max total jobs
THRESHOLD_ALL = 10000
# max age in days for running jobs
THRESHOLD_AGE = 5
# max percent usage of predefined FSs
THRESHOLD_DF = 90
FS_TO_CHECK = ["/mnt/seq", "/mnt/projects/rpd", "/mnt/projects/userrig"]



def check_qstat():
    """run several checks on qstat

    warnings returned as strings/lines
    """

    qstat_cmd = ["qstat", "-u", "userrig"]
    warnings = ""
    try:
        _ = subprocess.check_output(qstat_cmd)
    except subprocess.CalledProcessError:
        warnings += ("[qstat fail]")
        return warnings

    count_qw = 0
    count_Eqw = 0
    count_all = 0
    for line in subprocess.check_output(qstat_cmd).splitlines():
        if str.isdigit(str(line.split()[0], "utf-8")):
            count_all += 1
            status = str(line.split()[4], "utf-8")
            if status == "qw":
                count_qw += 1
            if status == "Eqw":
                count_Eqw += 1
            if status == 'r':
                dt = datetime.datetime.strptime(str(line.split()[5], "utf-8"), "%m/%d/%Y")
                if ((datetime.date.today() - datetime.date(dt.year, dt.month, dt.day)).days) > THRESHOLD_AGE:
                    warnings += ("[age > " + str(THRESHOLD_AGE) + " days]:\t" + "job-ID " + str(line.split()[0], "utf-8") + "\n")
    if count_qw > THRESHOLD_QW:
        warnings += ("[qw > " + str(THRESHOLD_QW) + " jobs]:\t" + str(count_qw) + "\n")
    if count_Eqw > THRESHOLD_EQW:
        warnings += ("[Eqw > " + str(THRESHOLD_EQW) + " jobs]:\t" + str(count_Eqw) + "\n")
    if count_all > THRESHOLD_ALL:
        warnings += ("[all > " + str(THRESHOLD_ALL) + " jobs]:\t" + str(count_all) + "\n")
    return warnings



def check_df(fs_to_check):
    """check file systems usage

    warnings returned as strings/lines"""
    warnings = ""
    for fs in fs_to_check:
        l = []
        for line in subprocess.check_output(["df", "-h", fs]).splitlines():
            l.append(line.split())
        if int(l[2][3][:-1]) > THRESHOLD_DF:
            warnings += ("[Use% > " + str(THRESHOLD_DF) + "%]:\t" + dir + "\n")
    return warnings


#def send_email(email, subject, message):
#    subprocess.getoutput("echo '" + message + "' | mail -s '" + subject + "' " + email)


def main():
    #send_email("rpd@mailman.gis.a-star.edu.sg", "[RPD] Hourly Userrig Production Warnings", check_qstat() + check_df())
    warnings = check_qstat()
    warnings += check_df(FS_TO_CHECK)
    if len(warnings):
        print(warnings)



if __name__ == "__main__":
    main()
    # FIXME print cwd for jobs
