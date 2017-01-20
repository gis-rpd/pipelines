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
from datetime import datetime, timedelta
import calendar
import json
import tarfile
import glob

#--- third-party imports
#
import yaml
import requests

#--- project specific imports
#
from config import site_cfg
from config import rest_services


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


def get_downstream_outdir(requestor, pipeline_name, pipeline_version=None):
    """generate downstream output directory
    """

    if is_devel_version():
        basedir = site_cfg['downstream_outdir_base']['devel']
    else:
        basedir = site_cfg['downstream_outdir_base']['devel']
    if pipeline_version:
        pversion = pipeline_version
    else:
        pversion = get_pipeline_version(nospace=True)
    outdir = "{basedir}/{requestor}/{pversion}/{pname}/{ts}".format(
        basedir=basedir, requestor=requestor, pversion=pversion,
        pname=pipeline_name, ts=generate_timestamp())
    return outdir


class PipelineHandler(object):
    """FIXME:add-doc

    - FIXME needs cleaning up!
    - FIXME check access of global vars
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
    MASTER_WALLTIME_H = 120

    def __init__(self,
                 pipeline_name,
                 pipeline_subdir,
                 outdir,
                 user_data,
                 pipeline_rootdir=PIPELINE_ROOTDIR,
                 logger_cmd="true", # bash: not doing anything by default
                 site=None,
                 master_q=None,
                 slave_q=None,
                 master_walltime_h=MASTER_WALLTIME_H,
                 params_cfgfile=None,
                 modules_cfgfile=None,
                 refs_cfgfile=None,
                 cluster_cfgfile=None):
        """init function

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

        if params_cfgfile:
            assert os.path.exists(params_cfgfile)
        self.params_cfgfile = params_cfgfile

        if modules_cfgfile:
            assert os.path.exists(modules_cfgfile)
        self.modules_cfgfile = modules_cfgfile

        if refs_cfgfile:
            assert os.path.exists(refs_cfgfile)
        self.refs_cfgfile = refs_cfgfile

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
        self.logger_cmd = logger_cmd
        self.site = site
        self.master_q = master_q
        self.slave_q = slave_q
        self.master_walltime_h = master_walltime_h
        self.snakefile_abs = os.path.abspath(
            os.path.join(pipeline_subdir, "Snakefile"))
        assert os.path.exists(self.snakefile_abs)

        # cluster configs
        if self.cluster_cfgfile:
            self.cluster_cfgfile_out = os.path.join(outdir, "cluster.yaml")
        # else: local

        # run template
        self.run_template = os.path.join(
            pipeline_rootdir, "lib", "run.template.{}.sh".format(self.site))
        self.run_out = os.path.join(outdir, "run.sh")
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
            # FIXME make config var
            #fh.write("source activate snakemake-3.5.5-g9752cd7-catch-logger-cleanup\n")
            #fh.write("source activate snakemake-3.7.1\n")
            #fh.write("source activate snakemake-3.8.2\n")
            fh.write("source activate snakemake-3.9.1\n")


    def write_snakemake_env(self, overwrite=False):
        """creates rc file for use as 'bash prefix', which also loads modules defined in cfgfile
        """

        if not overwrite:
            assert not os.path.exists(self.snakemake_env_file), self.snakemake_env_file

        with open(self.snakemake_env_file, 'w') as fh_rc:
            fh_rc.write("# used as bash prefix within snakemake\n\n")
            fh_rc.write("# make sure module command is defined (non-login shell). see http://lmod.readthedocs.io/en/latest/030_installing.html\n")
            fh_rc.write("source /etc/bashrc\n")
            fh_rc.write("# load modules\n")
            fh_rc.write("{}\n".format(" ".join(get_init_call())))

            with open(self.pipeline_cfgfile_out) as fh_cfg:
                yaml_data = yaml.safe_load(fh_cfg)
                assert "modules" in yaml_data
                for k, v in yaml_data["modules"].items():
                    fh_rc.write("module load {}/{}\n".format(k, v))

            fh_rc.write("\n")
            fh_rc.write("# unofficial bash strict has to come last\n")
            fh_rc.write("set -euo pipefail;\n")


    def write_cluster_config(self):
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
            reffa = merged_cfg['references']['genome']
            if reffa:
                assert 'num_chroms' not in merged_cfg['references']
                merged_cfg['references']['num_chroms'] = len(list(
                    chroms_and_lens_from_fasta(reffa)))

        return merged_cfg


    def write_merged_cfg(self, force_overwrite=False):
        """writes config file for use in snakemake becaused on default config
        """

        config = self.read_cfgfiles()
        config.update(self.user_data)

        b = config.get('intervals')
        if b:
            # bed only makes if we have a reference
            f = config['references'].get('genome')
            assert bed_and_indexed_fa_are_compatible(b, f), (
                "{} not compatible with {}".format(b, f))

        assert 'ELM' not in config
        config['ELM'] = self.elm_data

        if not force_overwrite:
            assert not os.path.exists(self.pipeline_cfgfile_out)
        with open(self.pipeline_cfgfile_out, 'w') as fh:
            # default_flow_style=None(default)|True(least readable)|False(most readable)
            yaml.dump(config, fh, default_flow_style=False)


    def setup_env(self):
        """create run environment
        """

        logger.info("Creating run environment in %s", self.outdir)
        # create log dir recursively so that parent is created as well
        os.makedirs(os.path.join(self.outdir, self.log_dir_rel))
        os.makedirs(os.path.join(self.outdir, self.RC_DIR))

        if self.site != "local":
            self.write_cluster_config()
        self.write_merged_cfg()
        self.write_snakemake_env()
        self.write_snakemake_init(self.snakemake_init_file)
        self.write_run_template()


    def submit(self, no_run=False):
        """FIXME:add-doc
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
        cmd = ['git', 'describe', '--always', '--tags']
        try:
            res = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            commit = res.decode().strip()
        except (subprocess.CalledProcessError, OSError) as _:
            pass
        if commit:
            version = "{} commit {}".format(version, commit)
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
        cmd = ['RPD_TESTING=0'] + cmd
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


# FIXME real_name() works at NSCC and GIS:
# getent passwd wilma | cut -f 5 -d :  | rev | cut -f 2- -d ' ' | rev
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


def parse_regions_from_bed(bed):
    """yields regions from bed as three tuple
    """

    with open(bed) as fh:
        for line in fh:
            if line.startswith('#') or not len(line.strip()) or line.startswith('track '):
                continue
            chrom, start, end = line.split()[:3]
            start, end = int(start), int(end)
            yield (chrom, start, end)


def chroms_and_lens_from_fasta(fasta):
    """return sequence and their length as two tuple. derived from fai
    """

    fai = fasta + ".fai"
    assert os.path.exists(fai), ("{} not indexed".format(fasta))
    with open(fai) as fh:
        for line in fh:
            (s, l) = line.split()[:2]
            l = int(l)
            yield (s, l)


def bed_and_indexed_fa_are_compatible(bed, fasta):
    """checks whether samtools faidx'ed fasta is compatible with bed file
    """

    assert os.path.exists(bed), ("Missing file {}".format(bed))
    assert os.path.exists(fasta), ("Missing fasta index {}".format(fasta))

    bed_sqs = set([c for c, s, e in parse_regions_from_bed(bed)])
    fa_sqs = [c for c, l in chroms_and_lens_from_fasta(fasta)]

    return all([s in fa_sqs for s in bed_sqs])


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
    if os.path.exists(os.path.join(pipeline_outdir, bundle)) and not overwrite:
        logger.warning("Refusing to overwrite existing log bundle.")
        return

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
