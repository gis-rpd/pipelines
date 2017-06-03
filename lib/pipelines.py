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
#import socket
import time
from datetime import datetime
from datetime import timedelta
import calendar
import json
import tarfile
import glob
import argparse
import copy
from collections import deque

#--- third-party imports
#
import yaml
import requests
import dateutil.relativedelta

#--- project specific imports
#
from config import site_cfg
from config import rest_services
from utils import generate_timestamp
from utils import chroms_and_lens_from_fasta
from utils import bed_and_fa_are_compat


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

# dir relative to Snakefile where configs are to be found

# from address, i.e. users should reply to to this
# instead of rpd@gis to which we send email
# FIXME both to config or external file
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

WORKFLOW_COMPLETION_FLAGFILE = "WORKFLOW_COMPLETE"

DOWNSTREAM_OUTDIR_TEMPLATE = "{basedir}/{user}/{pipelinename}-version-{pipelineversion}/{timestamp}"


def snakemake_log_status(log):
    """
    Return exit status and timestamp (isoformat string) as tuple.
    Exit status is either "SUCCESS" or "ERROR" or None
    If exit status is None timestamp will be last seen timestamp or empty and the status unknown

    Parses last lines of log, which could look like
    [Fri Jun 17 11:13:16 2016] Exiting because a job execution failed. Look above for error message
    [Fri Jul 15 01:29:12 2016] 17 of 17 steps (100%) done
    [Thu Nov 10 22:45:27 2016] Nothing to be done.
    """

    # this is by design a bit fuzzy
    with open(log) as fh:
        last_lines = deque(fh, maxlen=60)
    status = None
    last_etime = None
    while last_lines: # iterate from end
        line = last_lines.pop()
        if "Refusing to overwrite existing log bundle" in line:
            continue
        if line.startswith("["):# time stamp required
            estr = line[1:].split("]")[0]
            try:
                etime = datetime.strptime(estr, '%a %b %d %H:%M:%S %Y').isoformat()
            except:
                continue
            if not last_etime:
                last_etime = etime# first is last. useful for undefined status
            if 'steps (100%) done' in line or "Nothing to be done" in line:
                status = "SUCCESS"
                break
            elif 'Exiting' in line or "Error" in line:
                status = "ERROR"
                break
    return status, etime


def get_downstream_outdir(requestor, pipeline_name, pipeline_version=None):
    """generate downstream output directory
    """

    if is_devel_version():
        basedir = site_cfg['downstream_outdir_base']['devel']
    else:
        basedir = site_cfg['downstream_outdir_base']['production']
    if pipeline_version:
        pversion = pipeline_version
    else:
        pversion = get_pipeline_version(nospace=True)
    outdir = DOWNSTREAM_OUTDIR_TEMPLATE.format(
        basedir=basedir, user=requestor, pipelineversion=pversion,
        pipelinename=pipeline_name, timestamp=generate_timestamp())
    return outdir



class PipelineHandler(object):
    """Class that handles setting up and calling pipelines
    """

    # output
    PIPELINE_CFGFILE = "conf.yaml"

    RC_DIR = "rc"

    RC_FILES = {
        # used to load snakemake
        'SNAKEMAKE_INIT' : os.path.join(RC_DIR, 'snakemake_init.rc'),
        # used as bash prefix within snakemakejobs
        'SNAKEMAKE_ENV' : os.path.join(RC_DIR, 'snakemake_env.rc'),
    }

    LOG_DIR_REL = "logs"
    MASTERLOG = os.path.join(LOG_DIR_REL, "snakemake.log")
    SUBMISSIONLOG = os.path.join(LOG_DIR_REL, "submission.log")

    # master max walltime in hours
    # note, this includes waiting for jobs in q
    MASTER_WALLTIME_H = 96

    def __init__(self, pipeline_name, pipeline_subdir,
                 def_args,
                 cfg_dict,
                 cluster_cfgfile=None,
                 logger_cmd=None,
                 site=None,
                 master_walltime_h=MASTER_WALLTIME_H):
        """init function

        - pipeline_subdir: where default configs can be found, i.e pipeline subdir
        - def_args: argparser args. only default_argparser handled, i.e. must be subset of that
        - logger_cmd: the logger command used in run.sh. bash's 'true' doesn't do anything. Uses downstream default with conf db-id if set to None and logging is on.
        """

        self.pipeline_name = pipeline_name
        self.pipeline_version = get_pipeline_version()# external function
        self.pipeline_subdir = pipeline_subdir

        self.log_dir_rel = self.LOG_DIR_REL
        self.masterlog = self.MASTERLOG
        self.submissionlog = self.SUBMISSIONLOG

        self.master_q = def_args.master_q
        self.slave_q = def_args.slave_q
        self.outdir = def_args.outdir

        self.cfg_dict = copy.deepcopy(cfg_dict)
        self.cfg_dict['mail_on_completion'] = not def_args.no_mail
        self.cfg_dict['mail_address'] = def_args.mail_address
        if def_args.name:
            self.cfg_dict['analysis_name'] = def_args.name

        if def_args.extra_conf:
            for keyvalue in def_args.extra_conf:
                assert keyvalue.count(":") == 1, ("Invalid argument for extra-conf")
                k, v = keyvalue.split(":")
                self.cfg_dict[k] = v

        if def_args.params_cfg:
            assert os.path.exists(def_args.params_cfg)
        self.params_cfgfile = def_args.params_cfg

        if def_args.modules_cfg:
            assert os.path.exists(def_args.modules_cfg)
        self.modules_cfgfile = def_args.modules_cfg

        if def_args.references_cfg:
            assert os.path.exists(def_args.references_cfg)
        self.refs_cfgfile = def_args.references_cfg

        if cluster_cfgfile:
            assert os.path.exists(cluster_cfgfile)
        self.cluster_cfgfile = cluster_cfgfile

        self.pipeline_cfgfile_out = os.path.join(
            self.outdir, self.PIPELINE_CFGFILE)

        # RCs
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

        # DB logging of execution
        if def_args.db_logging in ['n', 'no', 'off']:
            # use bash's true, which doesn't do anything
            self.logger_cmd = 'true'
        elif def_args.db_logging in ['y', 'yes', 'on']:
            # trust caller if given, otherwise use the default logger which depends on db-id
            if not logger_cmd:
                assert self.cfg_dict['db-id'], ("Need db-id config value for logging")
                # run.sh has a path to snakemake so should contain a path to python3
                scr = os.path.join(PIPELINE_ROOTDIR, 'downstream-handlers', 'downstream_started.py')
                logger_cmd = "{} -d {} -o {}".format(scr, self.cfg_dict['db-id'], self.outdir)
                self.logger_cmd = logger_cmd
        else:
            raise ValueError(def_args.db_logging)

        self.site = site
        self.master_walltime_h = master_walltime_h
        self.snakefile_abs = os.path.abspath(
            os.path.join(pipeline_subdir, "Snakefile"))
        assert os.path.exists(self.snakefile_abs)

        # cluster configs
        if self.cluster_cfgfile:
            self.cluster_cfgfile_out = os.path.join(self.outdir, "cluster.yaml")
        # else: local

        # run template
        self.run_template = os.path.join(
            PIPELINE_ROOTDIR, "lib", "run.template.{}.sh".format(self.site))
        self.run_out = os.path.join(self.outdir, "run.sh")
        assert os.path.exists(self.run_template)

        # we don't know for sure who's going to actually exectute
        # but it's very likely the current user, who needs to be notified
        # on qsub kills etc
        self.toaddr = email_for_user()

        log_path = os.path.abspath(os.path.join(self.outdir, self.masterlog))
        self.elm_data = {'pipeline_name': self.pipeline_name,
                         'pipeline_version': self.pipeline_version,
                         'site': self.site,
                         'instance_id': 'SET_ON_EXEC',# dummy
                         'submitter': 'SET_ON_EXEC',# dummy
                         'log_path': log_path}


    @staticmethod
    def write_snakemake_init(rc_file, overwrite=False):
        """write snakemake init rc (loads miniconda and, activate source')
        """
        if not overwrite:
            assert not os.path.exists(rc_file), rc_file
        with open(rc_file, 'w') as fh:
            # init first so that modules are present
            fh.write("{}\n".format(" ".join(get_init_call())))
            fh.write("module load miniconda3\n")
            fh.write("source activate {}\n".format(site_cfg['snakemake_env']))



    def write_snakemake_env(self, overwrite=False):
        """creates rc file for use as 'bash prefix', which also loads modules defined in cfgfile
        """

        if not overwrite:
            assert not os.path.exists(self.snakemake_env_file), self.snakemake_env_file

        with open(self.snakemake_env_file, 'w') as fh_rc:
            fh_rc.write("# used as bash prefix within snakemake\n\n")
            fh_rc.write("# make sure module command is defined (non-login shell). see http://lmod.readthedocs.io/en/latest/030_installing.html\n")
            fh_rc.write("{}\n".format(" ".join(get_init_call())))
            fh_rc.write("# load modules\n")
            with open(self.pipeline_cfgfile_out) as fh_cfg:
                yaml_data = yaml.safe_load(fh_cfg)
                assert "modules" in yaml_data
                for k, v in yaml_data["modules"].items():
                    fh_rc.write("module load {}/{}\n".format(k, v))

            fh_rc.write("\n")
            fh_rc.write("# unofficial bash strict has to come last\n")
            fh_rc.write("set -euo pipefail;\n")


    def write_cluster_cfg(self):
        """writes site dependend cluster config
        """
        shutil.copyfile(self.cluster_cfgfile, self.cluster_cfgfile_out)


    def write_run_template(self):
        """writes run template replacing placeholder with variables defined in
        instance
        """

        d = {'SNAKEFILE': self.snakefile_abs,
             'LOGDIR': self.log_dir_rel,
             'MASTERLOG': self.masterlog,
             'PIPELINE_NAME': self.pipeline_name,
             'MAILTO': self.toaddr,
             'MASTER_WALLTIME_H': self.master_walltime_h,
             'DEFAULT_SLAVE_Q': self.slave_q if self.slave_q else "",
             'LOGGER_CMD': self.logger_cmd}

        with open(self.run_template) as fh:
            templ = fh.read()
        with open(self.run_out, 'w') as fh:
            fh.write(templ.format(**d))


    def read_cfgfiles(self):
        """parse default config and replace all RPD env vars
        """

        merged_cfg = dict()
        rpd_vars = get_rpd_vars()

        for cfgkey, cfgfile in [('global', self.params_cfgfile),
                                ('references', self.refs_cfgfile),
                                ('modules', self.modules_cfgfile)]:
            if not cfgfile:
                continue
            with open(cfgfile) as fh:
                try:
                    cfg = dict(yaml.safe_load(fh))
                except:
                    logger.fatal("Loading %s failed", cfgfile)
                    raise
            # to replace rpd vars the trick is to traverse
            # dictionary fully and replace all instances
            dump = json.dumps(cfg)
            for k, v in rpd_vars.items():
                dump = dump.replace("${}".format(k), v)
            cfg = dict(json.loads(dump))
            if cfgkey == 'global':
                merged_cfg.update(cfg)
            else:
                assert cfgkey not in merged_cfg
                merged_cfg[cfgkey] = cfg
        # determine num_chroms needed by some pipelines
        # FIXME ugly because sometimes not needed
        if merged_cfg.get('references'):
            reffa = merged_cfg['references'].get('genome')
            if reffa:
                assert 'num_chroms' not in merged_cfg['references']
                merged_cfg['references']['num_chroms'] = len(list(
                    chroms_and_lens_from_fasta(reffa)))

        return merged_cfg


    def write_merged_cfg(self, force_overwrite=False):
        """writes config file for use in snakemake becaused on default config
        """

        master_cfg = self.read_cfgfiles()
        master_cfg.update(self.cfg_dict)

        b = master_cfg.get('intervals')
        # sanity check: bed only makes sense if we have a reference
        if b:
            f = master_cfg['references'].get('genome')
            assert bed_and_fa_are_compat(b, f), (
                "{} not compatible with {}".format(b, f))

        assert 'ELM' not in master_cfg
        master_cfg['ELM'] = self.elm_data

        if not force_overwrite:
            assert not os.path.exists(self.pipeline_cfgfile_out)
        with open(self.pipeline_cfgfile_out, 'w') as fh:
            # default_flow_style=None(default)|True(least readable)|False(most readable)
            yaml.dump(master_cfg, fh, default_flow_style=False)


    def setup_env(self):
        """create run environment
        """

        logger.info("Creating run environment in %s", self.outdir)
        # create log dir recursively so that parent is created as well
        os.makedirs(os.path.join(self.outdir, self.log_dir_rel))
        os.makedirs(os.path.join(self.outdir, self.RC_DIR))

        if self.site != "local":
            self.write_cluster_cfg()
        self.write_merged_cfg()
        self.write_snakemake_env()
        self.write_snakemake_init(self.snakemake_init_file)
        self.write_run_template()


    def submit(self, no_run=False):
        """submit pipeline run
        """

        if self.master_q:
            master_q_arg = "-q {}".format(self.master_q)
        else:
            master_q_arg = ""
        if self.site == "local":
            logger.warning("Please not that script is run in 'local' mode"
                           " (which is mainly for debugging)")
            cmd = "cd {} && bash {} {} >> {}".format(
                os.path.dirname(self.run_out), master_q_arg,
                os.path.basename(self.run_out), self.submissionlog)
        else:
            cmd = "cd {} && {} {} {} >> {}".format(
                os.path.dirname(self.run_out), site_cfg['master_submission_cmd'], 
                master_q_arg, os.path.basename(self.run_out), self.submissionlog)

        if no_run:
            logger.warning("Skipping pipeline run on request. Once ready, use: %s", cmd)
            logger.warning("Once ready submit with: %s", cmd)
        else:
            logger.info("Starting pipeline: %s", cmd)
            #os.chdir(os.path.dirname(run_out))
            try:
                res = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                # if cluster has not compute nodes (e.g. AWS
                # autoscaling to 0), UGE will throw an error, but job
                # still gets submitted
                if 'job is not allowed to run in any queue' in e.output.decode():
                    logger.warning("Looks like cluster cooled down (no compute nodes available)."
                                   " Job is submitted nevertheless and should start soon.")
                else:
                    raise

            submission_log_abs = os.path.abspath(os.path.join(
                self.outdir, self.submissionlog))
            master_log_abs = os.path.abspath(os.path.join(
                self.outdir, self.masterlog))
            logger.debug("For submission details see %s", submission_log_abs)
            logger.info("The (master) logfile is %s", master_log_abs)


def default_argparser(cfg_dir, allow_missing_cfgfile=False):
    """Create default argparser (use as parent) for pipeline calls. Needs
    point to pipelines config dir
    """

    parser = argparse.ArgumentParser(add_help=False)
    parser._optionals.title = "Output"
    parser.add_argument('-o', "--outdir", required=True,
                        help="Output directory (must not exist)")

    rep_group = parser.add_argument_group('Reporting')
    rep_group.add_argument('--name',
                           help="Give this analysis run a name (used in email and report)")
    rep_group.add_argument('--no-mail', action='store_true',
                           help="Don't send mail on completion")
    default = email_for_user()
    rep_group.add_argument('--mail', dest='mail_address', default=default,
                           help="Send completion emails to this address (default: {})".format(default))
    default = "y" if is_production_user() else 'n'
    rep_group.add_argument('--db-logging', choices=('y', 'n'), default=default,
                           #help=argparse.SUPPRESS)# hidden
                           help="Log execution in DB: n=no; y=yes (only allowed as production user))")
    rep_group.add_argument('-v', '--verbose', action='count', default=0,
                           help="Increase verbosity")
    rep_group.add_argument('-q', '--quiet', action='count', default=0,
                           help="Decrease verbosity")

    q_group = parser.add_argument_group('Run behaviour')
    default = get_default_queue('slave')
    q_group.add_argument('-w', '--slave-q', default=default,
                         help="Queue to use for slave jobs (default: {})".format(default))
    default = get_default_queue('master')
    q_group.add_argument('-m', '--master-q', default=default,
                         help="Queue to use for master job (default: {})".format(default))
    q_group.add_argument('-n', '--no-run', action='store_true')

    cfg_group = parser.add_argument_group('Configuration')
    cfg_group.add_argument('--extra-conf', nargs='*', metavar="key:value",
                           help="Advanced: Extra values written added config (overwriting values).")
    cfg_group.add_argument('--sample-cfg',
                           help="Config-file (YAML) listing samples and readunits."
                           " Collides with -1, -2 and -s")
    for name, descr in [("references", "reference sequences"),
                        ("params", "parameters"),
                        ("modules", "modules")]:
        cfg_file = os.path.abspath(os.path.join(cfg_dir, "{}.yaml".format(name)))
        if not os.path.exists(cfg_file):
            if allow_missing_cfgfile:
                cfg_file = None
            else:
                raise ValueError((cfg_file, allow_missing_cfgfile))
        cfg_group.add_argument('--{}-cfg'.format(name),
                               default=cfg_file,
                               help="Config-file (yaml) for {}. (default: {})".format(descr, default))

    return parser


def get_pipeline_version(nospace=False):
    """determine pipeline version as defined by updir file
    """
    version_file = os.path.abspath(os.path.join(PIPELINE_ROOTDIR, "VERSION"))
    with open(version_file) as fh:
        version = fh.readline().strip()
    cwd = os.getcwd()
    os.chdir(PIPELINE_ROOTDIR)
    if os.path.exists(".git"):
        commit = None
        cmd = ['git', 'rev-parse', '--short', 'HEAD']
        try:
            res = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            commit = res.decode().strip()
        except (subprocess.CalledProcessError, OSError) as _:
            pass
        if commit:
            version = "{} {}".format(version, commit)
    if nospace:
        version = version.replace(" ", "-")
    os.chdir(cwd)
    return version


def is_devel_version():
    """checks whether this is a developers version of production
    """
    check_file = os.path.abspath(os.path.join(PIPELINE_ROOTDIR, "DEVELOPERS_VERSION"))
    #logger.debug("check_file = {}".format(check_file))
    return os.path.exists(check_file)


def get_site():
    """Where are we running
    """
    return site_cfg['name']


def get_cluster_cfgfile(cfg_dir):
    """returns None for local runs
    """
    site = get_site()
    if site != "local":
        cfg = os.path.join(cfg_dir, "cluster.{}.yaml".format(site))
        assert os.path.exists(cfg), ("Missing file {}".format(cfg))
        return cfg


def get_init_call():
    """return dotkit init call
    """
    cmd = ['source', site_cfg['init']]
    if is_devel_version():
        cmd = ['RPD_TESTING=1'] + cmd
    return cmd


def get_rpd_vars():
    """Read RPD variables set by calling and parsing output from init
    """

    cmd = get_init_call()
    cmd = ' '.join(cmd) + ' && set | grep "^RPD_"'
    try:
        res = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        logger.fatal("Couldn't call init %s. Result was: %s", cmd, res)
        raise
    rpd_vars = dict()
    for line in res.decode().splitlines():
        if line.startswith('RPD_') and '=' in line:
            #line = line.replace("export ", "")
            #line = ''.join([c for c in line if c not in '";\''])
            #logger.debug("line = {}".format(line))
            k, v = line.split('=')
            rpd_vars[k.strip()] = v.strip()
    return rpd_vars


def isoformat_to_epoch_time(ts):
    """
    Converts ISO8601 format (analysis_id) into epoch time
    """
    dt = datetime.strptime(ts[:-7], '%Y-%m-%dT%H-%M-%S.%f')-\
         timedelta(hours=int(ts[-5:-3]),
                   minutes=int(ts[-2:]))*int(ts[-6:-5]+'1')
    epoch_time = calendar.timegm(dt.timetuple()) + dt.microsecond/1000000.0
    return epoch_time


def relative_epoch_time(epoch_time1, epoch_time2):
    """
    Relative time difference between two epoch time
    """
    dt1 = datetime.fromtimestamp(epoch_time1)
    dt2 = datetime.fromtimestamp(epoch_time2)
    rd = dateutil.relativedelta.relativedelta(dt1, dt2)
    return rd


def get_machine_run_flowcell_id(runid_and_flowcellid):
    """return machine-id, run-id and flowcell-id from full string.
    Expected string format is machine-runid_flowcellid

    >>> get_machine_run_flowcell_id("HS002-SR-R00224_BC9A6MACXX")
    ('HS002', 'HS002-SR-R00224', 'BC9A6MACXX')
    >>> get_machine_run_flowcell_id("/path/to/seq/HS002-SR-R00224_BC9A6MACXX")
    ('HS002', 'HS002-SR-R00224', 'BC9A6MACXX')
    >>> get_machine_run_flowcell_id("HS002_SR_R00224_BC9A6MACXX")
    Traceback (most recent call last):
      ...
    AssertionError: Wrong format: HS002_SR_R00224_BC9A6MACXX
    """
    
    # strip away path
    runid_and_flowcellid = runid_and_flowcellid.rstrip("/").split('/')[-1]
    assert runid_and_flowcellid.count("_") == 1, (
        "Wrong format: {}".format(runid_and_flowcellid))
    runid, flowcellid = runid_and_flowcellid.split("_")
    machineid = runid.split("-")[0]
    return machineid, runid, flowcellid


def email_for_user():
    """get email for user (naive)
    """

    user_name = getuser()
    if user_name == "userrig":
        toaddr = "rpd@gis.a-star.edu.sg"
    else:
        toaddr = "{}@gis.a-star.edu.sg".format(user_name)
    return toaddr


def is_production_user():
    """true if run as production user
    """
    return getuser() == "userrig"


def get_default_queue(master_or_slave):
    """return cluster queue (for current user)
    """

    if is_production_user():
        user = 'production'
    else:
        user = 'enduser'
    key = 'default_{}_q'.format(master_or_slave)
    return site_cfg[key][user]


def send_status_mail(pipeline_name, success, analysis_id, outdir,
                     extra_text=None, pass_exception=True, to_address=None):
    """
    - pipeline_name: pipeline name
    - success: bool
    - analysis_id:  name/identifier for this analysis run
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
    if to_address:
        msg['To'] = to_address
    else:
        msg['To'] = email_for_user()

    server = smtplib.SMTP(site_cfg['smtp_server'])
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

    server = smtplib.SMTP(site_cfg['smtp_server'])
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


def path_to_url(out_path):
    """convert path to qlap33 server url"""

    # FIXME change for testing, gis, NSCC
    if out_path.startswith("/mnt/projects/userrig/solexa/"):
        return out_path.replace("/mnt/projects/userrig/solexa/", \
            "http://rpd/userrig/runs/solexaProjects/")
    else:
        #raise ValueError(out_path)
        return out_path


def mux_to_lib(mux_id, testing=False):
    """returns the component libraries for MUX
    """
    lib_list = []
    if not testing:
        rest_url = rest_services['lib_details']['production'].replace("lib_id", mux_id)
    else:
        rest_url = rest_services['lib_details']['testing'].replace("lib_id", mux_id)
    response = requests.get(rest_url)
    if response.status_code != requests.codes.ok:
        response.raise_for_status()
    rest_data = response.json()
    if 'plexes' not in rest_data:
        logger.fatal("FATAL: plexes info for %s is not available in ELM \n", mux_id)
        sys.exit(1)
    for lib in rest_data['plexes']:
        lib_list.append(lib['libraryId'])
    return lib_list


def bundle_and_clean_logs(pipeline_outdir, result_outdir="out/",
                          log_dir="logs/", overwrite=False):
    """bundle log files in pipeline_outdir+result_outdir and
    pipeline_outdir+log_dir to pipeline_outdir+logs.tar.gz and remove

    See http://stackoverflow.com/questions/40602894/access-to-log-files for potential alternatives
    """

    for d in [pipeline_outdir,
              os.path.join(pipeline_outdir, result_outdir),
              os.path.join(pipeline_outdir, log_dir)]:
        if not os.path.exists(d):
            logger.warning("Missing directory %s. Skipping log bundling.", d)
            return

    bundle = os.path.join(log_dir, "logs.tar.gz")# relative to pipeline_outdir
    if not overwrite and os.path.exists(os.path.join(pipeline_outdir, bundle)):
        bundle = os.path.join(log_dir, "logs.{}.tar.gz".format(generate_timestamp()))
        assert not os.path.exists(os.path.join(pipeline_outdir, bundle))

    orig_dir = os.getcwd()
    os.chdir(pipeline_outdir)
    # all log files associated with output files
    logfiles = glob.glob(os.path.join(result_outdir, "**/*.log"), recursive=True)
    # (cluster) log directory
    logfiles.extend(glob.glob(os.path.join(log_dir, "*")))
    # paranoid cleaning and some exclusion
    logfiles = [f for f in logfiles if os.path.isfile(f)
                and not f.endswith("snakemake.log")]

    with tarfile.open(bundle, "w:gz") as tarfh:
        for f in logfiles:
            tarfh.add(f)
            os.unlink(f)

    os.chdir(orig_dir)


def mark_as_completed():
    """Dropping a flag file marking analysis as complete"""
    analysis_dir = os.getcwd()
    flag_file = os.path.join(analysis_dir, WORKFLOW_COMPLETION_FLAGFILE)
    with open(flag_file, 'a') as fh:
        fh.write("{}\n".format(generate_timestamp()))
