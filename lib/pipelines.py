"""library functions for pipelines
"""

#--- standard library imports
#
import os
#import sys
import subprocess
import logging
import shutil
import smtplib
from email.mime.text import MIMEText
from getpass import getuser
#import socket
import time
from datetime import datetime, timedelta
import calendar
import json

#--- third-party imports
#
import yaml

#--- project specific imports
#
from services import SMTP_SERVER


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# only dump() and following do not automatically create aliases
yaml.Dumper.ignore_aliases = lambda *args: True


# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)



INIT = {
    # FIXME make env instead? because caller knows, right?
    'GIS': "/mnt/projects/rpd/init",
    'NSCC': "/seq/astar/gis/rpd/init"
}

# from address, i.e. users should reply to to this
# instead of rpd@gis to which we send email
RPD_MAIL = "rpd@gis.a-star.edu.sg"
RPD_SIGNATURE = """
--
Research Pipeline Development Team
Scientific & Research Computing
<{}>
""".format(RPD_MAIL)


# ugly
PIPELINE_ROOTDIR = os.path.join(os.path.dirname(__file__), "..")
assert os.path.exists(os.path.join(PIPELINE_ROOTDIR, "VERSION"))


class PipelineHandler(object):
    """FIXME:add-doc

    - FIXME needs cleaning up!
    - FIXME check access of global vars
    """

    PIPELINE_CONFIG_FILE = "conf.yaml"
    PIPELINE_DEFAULT_CONFIG_FILE = "conf.default.yaml"

    RC_DIR = "rc"

    RC_FILES = {
        'DK_INIT' : os.path.join(RC_DIR, 'dk_init.rc'),# used to load dotkit
        'SNAKEMAKE_INIT' : os.path.join(RC_DIR, 'snakemake_init.rc'),# used to load snakemake
        'SNAKEMAKE_ENV' : os.path.join(RC_DIR, 'snakemake_env.rc'),# used as bash prefix within snakemakejobs
    }

    LOG_DIR_REL = "logs"
    MASTERLOG = os.path.join(LOG_DIR_REL, "snakemake.log")
    SUBMISSIONLOG = os.path.join(LOG_DIR_REL, "submission.log")

    # master max walltime in hours
    # note, this includes waiting for jobs in q
    MASTER_WALLTIME_H = 120

    def __init__(self,
                 pipeline_name,
                 pipeline_subdir,
                 outdir,
                 user_data,
                 pipeline_rootdir=PIPELINE_ROOTDIR,
                 site=None,
                 master_q=None,
                 slave_q=None,
                 master_walltime_h=MASTER_WALLTIME_H):
        """FIXME:add-doc

        pipeline_subdir: where default configs can be found, i.e pipeline subdir
        """

        self.outdir = outdir
        self.pipeline_name = pipeline_name
        self.pipeline_version = get_pipeline_version()# external function
        self.pipeline_subdir = pipeline_subdir
        self.user_data = user_data

        self.log_dir_rel = self.LOG_DIR_REL
        self.masterlog = self.MASTERLOG
        self.submissionlog = self.SUBMISSIONLOG
        self.pipeline_config_out = os.path.join(
            self.outdir, self.PIPELINE_CONFIG_FILE)
        self.pipeline_default_config_file = os.path.join(
            pipeline_subdir, self.PIPELINE_DEFAULT_CONFIG_FILE)

        # RCs
        self.dk_init_file = os.path.join(
            self.outdir, self.RC_FILES['DK_INIT'])
        self.snakemake_init_file = os.path.join(
            self.outdir, self.RC_FILES['SNAKEMAKE_INIT'])
        self.snakemake_env_file = os.path.join(
            self.outdir, self.RC_FILES['SNAKEMAKE_ENV'])

        if site is None:
            try:
                site = get_site()
            except ValueError:
                logger.warning("Unknown site")
                site = "local"
        self.site = site
        self.master_q = master_q
        self.slave_q = slave_q
        self.master_walltime_h = master_walltime_h
        self.snakefile_abs = os.path.abspath(os.path.join(pipeline_subdir, "Snakefile"))
        assert os.path.exists(self.snakefile_abs)

        # cluster configs
        self.cluster_config_in = os.path.join(
            pipeline_subdir, "cluster.{}.yaml".format(site))
        self.cluster_config_out = os.path.join(outdir, "cluster.yaml")
        assert os.path.exists(self.cluster_config_in)

        # run template
        self.run_template = os.path.join(pipeline_rootdir, "lib",
                                         "run.template.{}.sh".format(self.site))
        self.run_out = os.path.join(outdir, "run.sh")
        assert os.path.exists(self.run_template)

        # we don't know for sure who's going to actually exectute
        # but it's very likely the current user, who needs to be notified
        # on qsub kills etc
        self.toaddr = email_for_user()

        self.elm_data = {'pipeline_name': self.pipeline_name,
                         'pipeline_version': self.pipeline_version,
                         'site': self.site,
                         'instance_id': 'SET_ON_EXEC',# dummy
                         'submitter': 'SET_ON_EXEC',# dummy
                         'log_path': os.path.abspath(os.path.join(self.outdir, self.masterlog))}


    @staticmethod
    def write_dk_init(rc_file, overwrite=False):
        """write dotkit init rc
        """
        if not overwrite:
            assert not os.path.exists(rc_file), rc_file
        with open(rc_file, 'w') as fh:
            fh.write("eval `{}`;\n".format(' '.join(get_init_call())))


    @staticmethod
    def write_snakemake_init(rc_file, overwrite=False):
        """write snakemake init rc (loads miniconda and, activate source')
        """
        if not overwrite:
            assert not os.path.exists(rc_file), rc_file
        with open(rc_file, 'w') as fh:
            fh.write("# initialize snakemake. requires pre-initialized dotkit\n")
            fh.write("reuse -q miniconda-3\n")
            #fh.write("source activate snakemake-3.5.5-g9752cd7-catch-logger-cleanup\n")
            fh.write("source activate snakemake-3.7.1\n")


    def write_snakemake_env(self, overwrite=False):
        """creates rc file for use as 'bash prefix', which also loads modules defined in config_file
        """

        if not overwrite:
            assert not os.path.exists(self.snakemake_env_file), self.snakemake_env_file

        with open(self.snakemake_env_file, 'w') as fh_rc:
            fh_rc.write("# used as bash prefix within snakemake\n\n")
            fh_rc.write("# init dotkit\n")
            fh_rc.write("source {}\n\n".format(os.path.relpath(self.dk_init_file, self.outdir)))

            fh_rc.write("# load modules\n")
            with open(self.pipeline_config_out) as fh_cfg:
                yaml_data = yaml.safe_load(fh_cfg)
                assert "modules" in yaml_data
                for k, v in yaml_data["modules"].items():
                    fh_rc.write("reuse -q {}\n".format("{}-{}".format(k, v)))

            fh_rc.write("\n")
            fh_rc.write("# unofficial bash strict has to come last\n")
            fh_rc.write("set -euo pipefail;\n")


    def write_cluster_config(self):
        """writes site dependend cluster config
        """
        shutil.copyfile(self.cluster_config_in, self.cluster_config_out)


    def write_run_template(self):
        """FIXME:add-doc
        """

        with open(self.run_template) as templ_fh, open(self.run_out, 'w') as out_fh:
            for line in templ_fh:
                # if we copied the snakefile (to allow for local modification)
                # the rules import won't work.  so use the original file
                line = line.replace("@SNAKEFILE@", self.snakefile_abs)
                line = line.replace("@LOGDIR@", self.log_dir_rel)
                line = line.replace("@MASTERLOG@", self.masterlog)
                line = line.replace("@PIPELINE_NAME@", self.pipeline_name)
                line = line.replace("@MAILTO@", self.toaddr)
                line = line.replace("@MASTER_WALLTIME_H@", str(self.master_walltime_h))
                if self.slave_q:
                    line = line.replace("@DEFAULT_SLAVE_Q@", self.slave_q)
                else:
                    line = line.replace("@DEFAULT_SLAVE_Q@", "")
                out_fh.write(line)


    def read_default_config(self):
        """parse default config and replace all RPD env vars
        """

        rpd_vars = get_rpd_vars()
        with open(self.pipeline_default_config_file) as fh:
            cfg = yaml.safe_load(fh)
        # trick to traverse dictionary fully and replace all instances of variable
        dump = json.dumps(cfg)
        for k, v in rpd_vars.items():
            dump = dump.replace("${}".format(k), v)
        cfg = dict(json.loads(dump))
        return cfg



    def write_merged_cfg(self, force_overwrite=False):
        """writes config file for use in snakemake becaused on default config
        """

        config = self.read_default_config()
        config.update(self.user_data)
        assert 'ELM' not in config
        config['ELM'] = self.elm_data

        if not force_overwrite:
            assert not os.path.exists(self.pipeline_config_out)
        with open(self.pipeline_config_out, 'w') as fh:
            # default_flow_style=None(default)|True(least readable)|False(most readable)
            yaml.dump(config, fh, default_flow_style=False)


    def setup_env(self):
        """FIXME:add-doc
        """

        logger.info("Creating run environment in %s", self.outdir)
        # create log dir recursively so that parent is created as well
        os.makedirs(os.path.join(self.outdir, self.log_dir_rel))
        os.makedirs(os.path.join(self.outdir, self.RC_DIR))

        self.write_cluster_config()
        self.write_merged_cfg()
        self.write_snakemake_env()
        self.write_dk_init(self.dk_init_file)
        self.write_snakemake_init(self.snakemake_init_file)
        self.write_run_template()



    def submit(self, no_run=False):
        """FIXME:add-doc
        """

        if self.master_q:
            master_q_arg = "-q {}".format(self.master_q)
        else:
            master_q_arg = ""
        cmd = "cd {} && qsub {} {} >> {}".format(
            os.path.dirname(self.run_out), master_q_arg,
            os.path.basename(self.run_out), self.submissionlog)
        if no_run:
            logger.warning("Skipping pipeline run on request. Once ready, use: %s", cmd)
            logger.warning("Once ready submit with: %s", cmd)
        else:
            logger.info("Starting pipeline: %s", cmd)
            #os.chdir(os.path.dirname(run_out))
            _ = subprocess.check_output(cmd, shell=True)
            submission_log_abs = os.path.abspath(os.path.join(self.outdir, self.submissionlog))
            master_log_abs = os.path.abspath(os.path.join(self.outdir, self.masterlog))
            logger.debug("For submission details see %s", submission_log_abs)
            logger.info("The (master) logfile is %s", master_log_abs)



def get_pipeline_version():
    """determine pipeline version as defined by updir file
    """
    version_file = os.path.abspath(os.path.join(PIPELINE_ROOTDIR, "VERSION"))
    with open(version_file) as fh:
        version = fh.readline().strip()
    cwd = os.getcwd()
    os.chdir(PIPELINE_ROOTDIR)
    if os.path.exists(".git"):
        commit = None
        cmd = ['git', 'describe', '--always', '--dirty']
        try:
            res = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            commit = res.decode().strip()
        except (subprocess.CalledProcessError, OSError) as _:
            pass
        if commit:
            version = "{} commit {}".format(version, commit)
    os.chdir(cwd)
    return version


def is_devel_version():
    """checks whether this is a developers version of production
    """
    check_file = os.path.abspath(os.path.join(PIPELINE_ROOTDIR, "DEVELOPERS_VERSION"))
    #logger.debug("check_file = {}".format(check_file))
    return os.path.exists(check_file)


def get_site():
    """Determine site where we're running. Throws ValueError if unknown
    """
    # gis detection is a bit naive... but socket.getfqdn() doesn't help here
    # also possible: ip a | grep -q 192.168.190 && NSCC=1
    if os.path.exists('/home/astar/gis'):# 'NSCC' in socket.getfqdn():
        return "NSCC"
    elif os.path.exists("/mnt/projects/rpd/") and os.path.exists("/mnt/software"):
        return "GIS"
    else:
        raise ValueError("unknown site")


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
    dt = datetime.strptime(ts[:-7], '%Y-%m-%dT%H-%M-%S.%f')-\
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


def send_status_mail(pipeline_name, success, analysis_id, outdir,
                     extra_text=None, pass_exception=True):
    """analysis_id should be unique identifier for this analysis

    - success: bool
    - analysis_id: analysis run id
    - outdir: directory where results are found
    """

    body = "Pipeline {} (version {}) for {} ".format(
        pipeline_name, get_pipeline_version(), analysis_id)
    if success:
        status_str = "completed"
        body += status_str
        body += "\n\nResults can be found in {}\n".format(outdir)
    else:
        status_str = "failed"
        body += status_str
        masterlog = os.path.normpath(os.path.join(outdir, "..", PipelineHandler.MASTERLOG))
        body += "\n\nSorry about this."
        body += "\n\nThe following log file provides more information: {}".format(masterlog)
    if extra_text:
        body = body + "\n" + extra_text + "\n"
    body += "\n\nThis is an automatically generated email\n"
    body += RPD_SIGNATURE

    site = get_site()
    subject = "Pipeline {} for {} {} (@{})".format(
        pipeline_name, analysis_id, status_str, site)

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = RPD_MAIL
    msg['To'] = email_for_user()

    site = get_site()
    server = smtplib.SMTP(SMTP_SERVER[site])
    try:
        server.send_message(msg)
        server.quit()
    except Exception as err:
        logger.fatal("Sending mail failed: %s", err)
        if not pass_exception:
            raise



def send_mail(subject, body, toaddr=None, ccaddr=None,
              pass_exception=True):
    """
    Generic mail function

    FIXME make toaddr and ccaddr lists
    """

    body += "\n"
    body += "\n\nThis is an automatically generated email\n"
    body += RPD_SIGNATURE

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = RPD_MAIL
    if toaddr is None:
        msg['To'] = email_for_user()
    elif "@" in toaddr:
        msg['To'] = toaddr
    else:
        msg['To'] = toaddr + "@gis.a-star.edu.sg"
    if ccaddr:
        if "@" not in ccaddr:
            ccaddr += "@gis.a-star.edu.sg"
        msg['Cc'] = ccaddr

    site = get_site()
    server = smtplib.SMTP(SMTP_SERVER[site])
    try:
        server.send_message(msg)
        server.quit()
    except Exception as err:
        logger.fatal("Sending mail failed: %s", err)
        if not pass_exception:
            raise


def ref_is_indexed(ref, prog="bwa"):
    """checks whether a reference was already indexed by given program"""

    if prog == "bwa":
        return all([os.path.exists(ref + ext)
                    for ext in [".pac", ".ann", ".amb", ".sa"]])
    elif prog == "samtools":
        return os.path.exists(ref + ".fai")
    else:
        raise ValueError


def generate_window(days=7):
    """returns tuple representing epoch window (int:present, int:past)"""
    date_time = time.strftime('%Y-%m-%d %H:%M:%S')
    pattern = '%Y-%m-%d %H:%M:%S'
    epoch_present = int(time.mktime(time.strptime(date_time, pattern)))*1000
    d = datetime.now() - timedelta(days=days)
    f = d.strftime("%Y-%m-%d %H:%m:%S")
    epoch_back = int(time.mktime(time.strptime(f, pattern)))*1000
    return (epoch_present, epoch_back)


def parse_regions_from_bed(bed):
    """yields regions from bed as three tuple
    """

    with open(bed) as fh:
        for line in fh:
            if line.startswith('#') or not len(line.strip()):
                continue
            chrom, start, end = line.split()[:3]
            start, end = int(start), int(end)
            yield (chrom, start, end)


def chroms_and_lens_from_from_fasta(fasta):
    """return sequence and their length as two tuple. derived from fai
    """

    fai = fasta + ".fai"
    assert os.path.exists(fai), ("{} not indexed".format(fasta))
    with open(fai) as fh:
        for line in fh:
            (s, l) = line.split()[:2]
            l = int(l)
            yield (s, l)


def path_to_url(out_path):
    """convert path to qlap33 server url"""

    # FIXME change for testing, gis, NSCC
    if out_path.startswith("/mnt/projects/userrig/solexa/"):
        return out_path.replace("/mnt/projects/userrig/solexa/", \
            "http://qlap33.gis.a-star.edu.sg/userrig/runs/solexaProjects/")
    else:
        #raise ValueError(out_path)
        return out_path
