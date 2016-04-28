"""library functions for pipelines
"""

#--- standard library imports
#
import os
import sys
import hashlib
import subprocess
import logging
import shutil
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from getpass import getuser
from itertools import zip_longest
import socket
from collections import namedtuple

#--- third-party imports
#
import yaml

#--- project specific imports
#/


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


ReadUnit = namedtuple('ReadUnit', ['run_id', 'flowcell_id', 'library_id',
                                   'lane_id', 'rg_id', 'fq1', 'fq2'])



# global logger
LOG = logging.getLogger(__name__)

INIT = {
    'gis': "/mnt/projects/rpd/init",
    # FIXME for NSCC alpha
    'nscc': "/home/astar/gis/wilma/rpd/init"
}


# FIXME hack: assuming importer is just one dir down of pipeline base dir
PIPELINE_BASEDIR = os.path.join(os.path.dirname(sys.argv[0]), "..")
# assert os.path.exists(os.path.join(PIPELINE_BASEDIR, "VERSION")), (PIPELINE_BASEDIR)
# we need functions from here in Snakefile as well, where the above breaks
if not os.path.exists(os.path.join(PIPELINE_BASEDIR, "VERSION")):
    # FIXME imported from wrong directory. Make sure everyone using PIPELINE_BASEDIR fails
    del PIPELINE_BASEDIR


def get_pipeline_version():
    """determine pipeline version as defined by updir file
    """
    version_file = os.path.abspath(os.path.join(PIPELINE_BASEDIR, "VERSION"))
    with open(version_file) as fh:
        version = fh.readline().strip()
    return version


def is_devel_version():
    """checks whether this is a developers version of production
    """
    check_file = os.path.abspath(os.path.join(PIPELINE_BASEDIR, "DEVELOPERS_VERSION"))
    #LOG.debug("check_file = {}".format(check_file))
    return os.path.exists(check_file)


def get_site():
    """Determine site where we're running. Throws ValueError if unknown
    """
    # gis detection is a bit naive... but socket.getfqdn() doesn't help here
    if os.path.exists("/mnt/projects/rpd/") and os.path.exists("/mnt/software"):
        return "gis"
    elif 'nscc' in socket.getfqdn() or socket.getfqdn().startswith('gis01'):
        return "nscc"
    else:
        raise ValueError("unknown site")


def get_init_call():
    """return dotkit init call
    """
    site = get_site()
    try:
        cmd = [INIT[get_site()]]
    except KeyError:
        raise ValueError("unknown or unconfigured or site {}".format(site))

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
        LOG.fatal("Couldn't call init as '{}'".format(' '.join(cmd)))
        raise

    rpd_vars = dict()
    for line in res.decode().splitlines():
        if line.startswith('export '):
            line = line.replace("export ", "")
            line = ''.join([c for c in line if c not in '";\''])
            #LOG.debug("line = {}".format(line))
            k, v = line.split('=')
            rpd_vars[k.strip()] = v.strip()
    return rpd_vars


def hash_for_fastq(fq1, fq2=None):
    """return hash for one or two fastq files based on filename only
    """
    m = hashlib.md5()
    m.update(fq1.encode())
    if fq2:
        m.update(fq2.encode())
    return m.hexdigest()


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


def write_cluster_config(outdir, basedir, force_overwrite=False):
    """writes site dependend cluster config

    basedir is where to find the input template (i.e. the pipeline directory)
    """
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


def get_machine_run_flowcell_id(runid_and_flowcellid):
    """return machine-id, run-id and flowcell-id from full string. Expected string format is machine-runid_flowcellid
    """
    # be lenient and allow full path
    runid_and_flowcellid = runid_and_flowcellid.rstrip("/").split('/')[-1]

    runid, flowcellid = runid_and_flowcellid.split("_")
    machineid = runid.split("-")[0]
    return machineid, runid, flowcellid


def send_status_mail(pipeline_name, success, id, outdir):
    """id should be unique identifier for this analysis
    """

    user_name = getuser()
    if user_name == "userrig":
        # FIXME rpd@mailman.gis.a-star.edu.sg in future
        toaddr = "veeravallil@gis.a-star.edu.sg"
    else:
        toaddr = "{}@gis.a-star.edu.sg".format(user_name)

    subject = "Pipeline {} {} for {}".format(
        pipeline_name, "completed" if success else "failed", id)

    body = "Please check logs in {}".format(outdir)
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = "rpd@mailman.gis.a-star.edu.sg"
    msg['To'] = toaddr

    # Send the mail
    try:
        server = smtplib.SMTP('localhost')
        server.send_message(msg)
        server.quit()
    except Exception:
        LOG.fatal("Sending mail failed")
        # FIXME consider exit 0 if pipeline breaks
        sys.exit(1)


def get_reads_unit_from_cfgfile(cfgfile):
    """FIXME:add-doc"""
    read_units = []
    with open(cfgfile) as fh_cfg:
        for entry in yaml.safe_load(fh_cfg):
            if len(entry) == 6:
                rg_id = None
                [run_id, flowcell_id, library_id, lane_id, fq1, fq2] = entry
            elif len(entry) == 7:
                [run_id, flowcell_id, library_id, lane_id, fq1, fq2, rg_id] = entry
            else:
                LOG.fatal("Couldn't parse read unit from '{}'".format(entry))
                raise ValueError(entry)

            # if we have relative paths, make them abs relative to cfgfile
            if fq1 and not os.path.isabs(fq1):
                fq1 = os.path.abspath(os.path.join(os.path.dirname(cfgfile), fq1))
            if fq2 and not os.path.isabs(fq2):
                fq2 = os.path.abspath(os.path.join(os.path.dirname(cfgfile), fq2))

            ru = ReadUnit._make([run_id, flowcell_id, library_id, lane_id,
                                 rg_id, fq1, fq2])
            if rg_id == 'None':
                ru = ru._replace(rg_id=create_rg_id_from_ru(ru))
            read_units.append(ru)
    return read_units


def get_reads_unit_from_args(fqs1, fqs2):
    """FIXME:add-doc"""

    read_units = []
    if not fqs2:
        fqs2 = len(fqs1)*[None]
    print_fq_sort_warning = False
    # sorting here should ensure R1 and R2 match
    fq_pairs = list(zip_longest(sorted(fqs1), sorted(fqs2)))
    fq_pairs_orig = set(zip_longest(fqs1, fqs2))
    for (fq1, fq2) in fq_pairs:
        if (fq1, fq2) not in fq_pairs_orig:
            print_fq_sort_warning = True
        run_id = flowcell_id = library_id = lane_id = rg_id = None
        ru = ReadUnit._make([run_id, flowcell_id, library_id, lane_id, rg_id, fq1, fq2])
        ru = ru._replace(rg_id=create_rg_id_from_ru(ru))
        read_units.append(ru)
    if print_fq_sort_warning:
        LOG.warn("Auto-sorted fq1 and fq2 files! Pairs are now processed as follows:\n{}".format(
            ' \n'.join(["{} and {}".format(fq1, fq2) for fq1, fq2 in fq_pairs])))
    return read_units


def key_for_read_unit(ru):
    """used for file nameing hence made unique based on fastq file names
    """
    return hash_for_fastq(ru.fq1, ru.fq2)


def create_rg_id_from_ru(ru):
    """Same RG for files coming from same source. If no source info is
    given use fastq files names
    """
    if all([ru.run_id, ru.library_id, ru.lane_id]):
        return "{}.{}".format(ru.run_id, ru.lane_id)
    elif ru.fq1:
        # no source info? then use fastq file names
        return hash_for_fastq(ru.fq1, ru.fq2)


def ref_is_indexed(ref, prog="bwa"):
    """checks whether a reference was already indexed by given program"""

    if prog == "bwa":
        return all([os.path.exists(ref + ext)
                    for ext in [".pac", ".ann", ".amb", ".sa"]])
    elif prog == "samtools":
        return os.path.exists(ref + ".fai")
    else:
        raise ValueError
