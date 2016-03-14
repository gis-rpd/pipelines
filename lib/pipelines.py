"""library functions for pipelines
"""

#--- standard library imports
#
import os
import sys
import hashlib
import subprocess
import logging

#--- third-party imports
#

#--- project specific imports
#/


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# global logger
LOG = logging.getLogger()

INIT = {
    'gis': "/mnt/projects/rpd/init"
}


# FIXME hack: assuming importer is just one dir down of pipeline base dir
PIPELINE_BASEDIR = os.path.join(os.path.dirname(sys.argv[0]), "..")
assert os.path.exists(os.path.join(PIPELINE_BASEDIR, "VERSION")), (PIPELINE_BASEDIR)



def get_pipeline_version():
    """determine pipeline version as defined by updir file
    """
    version_file = os.path.abspath(os.path.join(PIPELINE_BASEDIR, "VERSION"))
    with open(version_file) as fh:
        version = fh.readline().strip()
    return version


def testing_is_active():
    """checks whether this is a developers version of production
    """
    check_file = os.path.abspath(os.path.join(PIPELINE_BASEDIR, "DEVELOPERS_VERSION"))
    #LOG.debug("check_file = {}".format(check_file))
    return os.path.exists(check_file)


def get_site():
    """Determine site where we're running. Throws ValueError if unknown
    """
    # this is a bit naive... but socket.getfqdn() is also useless
    if os.path.exists("/mnt/projects/rpd/") and os.path.exists("/mnt/software"):
        return "gis"
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

    if testing_is_active():
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


