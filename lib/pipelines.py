"""library functions for pipelines
"""

#--- standard library imports
#
import os
import sys
import subprocess
import logging
import shutil
import smtplib
from email.mime.text import MIMEText
from getpass import getuser
import socket
import time
from datetime import datetime, timedelta
import calendar
import json

#--- third-party imports
#
import yaml

#--- project specific imports
#/


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)


#SMTP_SERVER = 'localhost'
SMTP_SERVER = 'mailman.gis.a-star.edu.sg'


INIT = {
    # FIXME make env instead? because caller knows, right?
    'gis': "/mnt/projects/rpd/init",
    'nscc': "/seq/astar/gis/rpd/init"
}

# from address, i.e. users should reply to to this
# instead of rpd@gis to which we send email
RPD_MAIL = "rpd@mailman.gis.a-star.edu.sg"
RPD_SIGNATURE = """
--
Research Pipeline Development Team
Scientific & Research Computing
<{}>
""".format(RPD_MAIL)


# ugly
PIPELINE_BASEDIR = os.path.join(os.path.dirname(__file__), "..")
assert os.path.exists(os.path.join(PIPELINE_BASEDIR, "VERSION"))


def read_default_config(pipeline_dir):
    """parse default config and replace all RPD env vars
    """
    rpd_vars = get_rpd_vars()
    # FIXME hardcoded name
    cfgfile = os.path.join(pipeline_dir, "conf.default.yaml".format())
    with open(cfgfile) as fh:
        cfg = yaml.safe_load(fh)
    # trick to traverse dictionary fully and replace all instances of variable
    dump = json.dumps(cfg)
    for k, v in rpd_vars.items():
        dump = dump.replace("${}".format(k), v)
    cfg = dict(json.loads(dump))
    return cfg



def get_pipeline_version():
    """determine pipeline version as defined by updir file
    """
    version_file = os.path.abspath(os.path.join(PIPELINE_BASEDIR, "VERSION"))
    with open(version_file) as fh:
        version = fh.readline().strip()
    cwd = os.getcwd()
    os.chdir(PIPELINE_BASEDIR)
    if os.path.exists(".git"):
        commit = None
        cmd = ['git', 'describe', '--always', '--dirty']
        try:
            res = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            commit = res.decode().strip()
        except (subprocess.CalledProcessError, OSError) as e:
            pass
        if commit:
            version = "{} commit {}".format(version, commit)
    os.chdir(cwd)
    return version


def is_devel_version():
    """checks whether this is a developers version of production
    """
    check_file = os.path.abspath(os.path.join(PIPELINE_BASEDIR, "DEVELOPERS_VERSION"))
    #logger.debug("check_file = {}".format(check_file))
    return os.path.exists(check_file)


def get_site():
    """Determine site where we're running. Throws ValueError if unknown
    """
    # gis detection is a bit naive... but socket.getfqdn() doesn't help here
    # also possible: ip a | grep -q 192.168.190 && NSCC=1
    if os.path.exists('/home/astar/gis'):# 'nscc' in socket.getfqdn():
        return "nscc"
    elif os.path.exists("/mnt/projects/rpd/") and os.path.exists("/mnt/software"):
        return "gis"
    else:
        raise ValueError("unknown site (fqdn was {})".format(socket.getfqdn()))


def get_init_call():
    """return dotkit init call
    """
    site = get_site()
    try:
        cmd = [INIT[get_site()]]
    except KeyError:
        raise ValueError("Unknown site '{}'".format(site))

    if is_devel_version():
        cmd.append('-d')

    return cmd


def get_rpd_vars():
    """Read RPD variables set by calling and parsing output from init
    """

    cmd = get_init_call()
    try:
        res = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        logger.fatal("Couldn't call init as '%s'", ' '.join(cmd))
        raise

    rpd_vars = dict()
    for line in res.decode().splitlines():
        if line.startswith('export '):
            line = line.replace("export ", "")
            line = ''.join([c for c in line if c not in '";\''])
            #logger.debug("line = {}".format(line))
            k, v = line.split('=')
            rpd_vars[k.strip()] = v.strip()
    return rpd_vars


def write_dk_init(rc_file, overwrite=False):
    """creates dotkit init rc
    """
    if not overwrite:
        assert not os.path.exists(rc_file), rc_file
    with open(rc_file, 'w') as fh:
        fh.write("eval `{}`;\n".format(' '.join(get_init_call())))


def write_snakemake_init(rc_file, overwrite=False):
    """creates file which loads snakemake
    """
    if not overwrite:
        assert not os.path.exists(rc_file), rc_file
    with open(rc_file, 'w') as fh:
        fh.write("# initialize snakemake. requires pre-initialized dotkit\n")
        fh.write("reuse -q miniconda-3\n")
        #fh.write("source activate snakemake-3.5.4\n")
        #fh.write("source activate snakemake-ga622cdd-onstart\n")
        #fh.write("source activate snakemake-3.5.5-onstart\n")
        fh.write("source activate snakemake-3.5.5-g9752cd7-catch-logger-cleanup\n")


def write_snakemake_env(rc_file, config, overwrite=False):
    """creates file for use as bash prefix within snakemake
    """
    if not overwrite:
        assert not os.path.exists(rc_file), rc_file

    with open(rc_file, 'w') as fh_rc:
        fh_rc.write("# used as bash prefix within snakemake\n\n")
        fh_rc.write("# init dotkit\n")
        fh_rc.write("source dk_init.rc\n\n")

        fh_rc.write("# load modules\n")
        with open(config) as fh_cfg:
            yaml_data = yaml.safe_load(fh_cfg)
            assert "modules" in yaml_data
            for k, v in yaml_data["modules"].items():
                fh_rc.write("reuse -q {}\n".format("{}-{}".format(k, v)))

        fh_rc.write("\n")
        fh_rc.write("# unofficial bash strict has to come last\n")
        fh_rc.write("set -euo pipefail;\n")


def write_cluster_config(outdir, basedir, force_overwrite=False, skip_unknown_site=False):
    """writes site dependend cluster config

    basedir is where to find the input template (i.e. the pipeline directory)
    """

    try:
        site = get_site()
    except ValueError:
        if skip_unknown_site:
            return
        else:
            raise
    cluster_config_in = os.path.join(basedir, "cluster.{}.yaml".format(get_site()))
    cluster_config_out = os.path.join(outdir, "cluster.yaml")

    assert os.path.exists(cluster_config_in)
    if not force_overwrite:
        assert not os.path.exists(cluster_config_out), cluster_config_out

    shutil.copyfile(cluster_config_in, cluster_config_out)


def generate_timestamp():
    """generate ISO8601 timestamp incl microsends, but with colons
    replaced to avoid problems if used as file name
    """
    return datetime.isoformat(datetime.now()).replace(":", "-")


def timestamp_from_string(analysis_id):
    """
    converts output of generate_timestamp(), e.g. 2016-05-09T16-43-32.080740 back to timestamp
    """
    dt = datetime.strptime(analysis_id, '%Y-%m-%dT%H-%M-%S.%f')
    return dt

def isoformat_to_epoch_time(ts):
    """
    Converts ISO8601 format (analysis_id) into epoch time
    """
    dt = datetime.strptime(ts[:-7],'%Y-%m-%dT%H-%M-%S.%f')-\
        timedelta(hours=int(ts[-5:-3]),
        minutes=int(ts[-2:]))*int(ts[-6:-5]+'1')
    epoch_time = calendar.timegm(dt.timetuple()) + dt.microsecond/1000000.0
    return epoch_time

def get_machine_run_flowcell_id(runid_and_flowcellid):
    """return machine-id, run-id and flowcell-id from full string.
    Expected string format is machine-runid_flowcellid
    """
    # be lenient and allow full path
    runid_and_flowcellid = runid_and_flowcellid.rstrip("/").split('/')[-1]

    runid, flowcellid = runid_and_flowcellid.split("_")
    machineid = runid.split("-")[0]
    return machineid, runid, flowcellid


# FIXME real_name() works at NSCC and GIS: getent passwd wilma | cut -f 5 -d :  | rev | cut -f 2- -d ' ' | rev
def email_for_user():
    """FIXME:add-doc
    """

    user_name = getuser()
    if user_name == "userrig":
        toaddr = "rpd@gis.a-star.edu.sg"
    else:
        toaddr = "{}@gis.a-star.edu.sg".format(user_name)
    return toaddr


def send_status_mail(pipeline_name, success, analysis_id, outdir, extra_text=None):
    """analysis_id should be unique identifier for this analysis

    - success: bool
    - analysis_id: analysis run id
    - outdir: directory where results are found
    """

    if success:
        status_str = "completed"
        body = "Pipeline {} (version {}) {} for {}.".format(
            pipeline_name, get_pipeline_version(), status_str, analysis_id)
        body += "\n\nResults can be found in {}\n".format(outdir)
    else:
        status_str = "failed"
        body = "Pipeline {} {} for {}".format(pipeline_name, status_str, analysis_id)
        # FIXME ugly inference of log folder
        logdir = os.path.normpath(os.path.join(outdir, "..", 'logs'))
        body += "\nSorry about this. Please check log files in {}".format(logdir)
    if extra_text:
        body = body + "\n" + extra_text + "\n"
    body += "\n\nThis is an automatically generated email\n"
    body += RPD_SIGNATURE

    subject = "Pipeline {} {} for {}".format(
        pipeline_name, status_str, analysis_id)

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = RPD_MAIL
    msg['To'] = email_for_user()

    # Send the mail
    try:
        server = smtplib.SMTP(SMTP_SERVER)
        server.send_message(msg)
        server.quit()
    except Exception:
        logger.fatal("Sending mail failed")
        # FIXME consider exit 0 if pipeline breaks
        sys.exit(1)

def send_report_mail(pipeline_name, Subject, extra_text, toaddr=None):
    """
    - pipeline_name: pipeline name or any report generation
    - extra_text: Body message of email
    """
    body = extra_text + "\n"
    body += "\n\nThis is an automatically generated email\n"
    body += RPD_SIGNATURE

    msg = MIMEText(body)
    msg['Subject'] = Subject
    msg['From'] = RPD_MAIL
    if toaddr is None:
        msg['To'] = email_for_user()
    elif "@" in toaddr:
        msg['To'] = toaddr
    else:
        msg['To'] = toaddr + "@gis.a-star.edu.sg"

    # Send the mail
    try:
        server = smtplib.SMTP(SMTP_SERVER)
        server.send_message(msg)
        server.quit()
    except Exception:
        logger.fatal("Sending mail failed")
        # FIXME consider exit 0 if pipeline breaks
        sys.exit(1)


def ref_is_indexed(ref, prog="bwa"):
    """checks whether a reference was already indexed by given program"""

    if prog == "bwa":
        return all([os.path.exists(ref + ext)
                    for ext in [".pac", ".ann", ".amb", ".sa"]])
    elif prog == "samtools":
        return os.path.exists(ref + ".fai")
    else:
        raise ValueError


#window for cronJob
def generate_window(days=7):
    """returns tuple representing epoch window (int:present, int:past)"""
    date_time = time.strftime('%Y-%m-%d %H:%M:%S')
    pattern = '%Y-%m-%d %H:%M:%S'
    epoch_present = int(time.mktime(time.strptime(date_time, pattern)))*1000
    d = datetime.now() - timedelta(days=days)
    f = d.strftime("%Y-%m-%d %H:%m:%S")
    epoch_back = int(time.mktime(time.strptime(f, pattern)))*1000
    return (epoch_present, epoch_back)

