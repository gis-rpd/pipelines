threshold_qw = 1000
threshold_Eqw = 0
threshold_all = 10000
threshold_age = 3
threshold_df = 90

# import argparse
# import os
import subprocess
import datetime
       
def check_qstat():
    warnings = ""
    if (subprocess.run(["qstat", "-u", "userrig"]).returncode == 0):
        count_qw = 0
        count_Eqw = 0
        count_all = 0
        for line in subprocess.check_output(["qstat", "-u", "userrig"]).splitlines():
            if (str.isdigit(str(line.split()[0], "utf-8"))):
                count_all += 1
                if (str(line.split()[4], "utf-8") == "qw"):
                    count_qw += 1
                if (str(line.split()[4], "utf-8") == "Eqw"):
                    count_Eqw += 1
                dt = datetime.datetime.strptime(str(line.split()[5], "utf-8"), "%m/%d/%Y")
                if (((datetime.date.today() - datetime.date(dt.year, dt.month, dt.day)).days) > threshold_age):
                    warnings += ("[age > " + str(threshold_age) + " days]:\t" + "job-ID " + str(line.split()[0], "utf-8") + "\n")
        if (count_qw > threshold_qw):
            warnings += ("[qw > " + str(threshold_qw) + " jobs]:\t" + str(count_qw) + "\n")
        if (count_Eqw > threshold_Eqw):
            warnings += ("[Eqw > " + str(threshold_Eqw) + " jobs]:\t" + str(count_Eqw) + "\n")
        if (count_all > threshold_all):
            warnings += ("[all > " + str(threshold_all) + " jobs]:\t" + str(count_all) + "\n")
    else:
        warnings += ("[ERROR]:\tqstat -u userrig\n")
    return warnings

def check_df():
    warnings = ""
    for dir in ["/mnt/seq", "/mnt/projects/rpd", "/mnt/projects/userrig"]:
        if (subprocess.run(["df", "-h", dir]).returncode == 0):
            l = []
            for line in subprocess.check_output(["df", "-h", dir]).splitlines():
                l.append(line.split())
            if (int(l[2][3][:-1]) > threshold_df):
                warnings += ("[Use% > " + str(threshold_df) + "%]:\t" + dir + "\n")
        else:
            warnings += ("[ERROR]:\t" + "df -h " + str(dir) + "\n")
    return warnings

def send_email(email, subject, message):
    subprocess.getoutput("echo '" + message + "' | mail -s '" + subject + "' " + email)

#send_email("rpd@mailman.gis.a-star.edu.sg", "[RPD] Hourly Userrig Production Warnings", check_qstat() + check_df())
print (check_qstat() + check_df())
