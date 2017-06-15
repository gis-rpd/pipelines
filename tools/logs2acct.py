#!/usr/bin/env python3
"""FIXME
"""

#--- standard library imports
#
import os
import sys
import glob
import re
import shlex
import subprocess

#--- third-party imports
#
#/

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
#LIB_PATH = os.path.abspath(
#    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
#if LIB_PATH not in sys.path:
#    sys.path.insert(0, LIB_PATH)
#from pipelines import get_downstream_outdir
#from pipelines import get_pipeline_version


__author__ = "Andreas WILM"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2017 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


#JOB_LOG_RE = '(?P<pipeline>[A-Za-z0-9-]+)\.(?P<jobtype>[A-Za-z0-9-]+)\.(?P<rule>[A-Za-z0-9-]+)\.(?P<smjobid>[0-9]+)\.sh\.o(?P<clusterjobid>[0-9]+)'
JOB_LOG_RE = '.*\.sh\.o([0-9]+)$'
ACCT_CMD = 'qacct -j {}'


def produce_acct_logs(cluster_log_dir, overwrite=False):
    """bundle log files in pipeline_outdir+result_outdir and"""

    for logf in glob.glob(os.path.join(cluster_log_dir, "*")):
        #print("Checking {}".format(logf))
        pattern = re.compile(JOB_LOG_RE)
        match = pattern.search(os.path.basename(logf))
        if not match:
            #print("Not a match {}".format(logf))
            continue

        acct_out = logf + ".acct"
        if os.path.exists(acct_out) and not overwrite:
            continue
        assert len(match.groups()) == 1
        jobid = match.groups()[0]
        cmd = shlex.split(ACCT_CMD.format(jobid))
        try:
            res = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            sys.stderr.write("Couldn't execute {}. Got {}. Skipping\n".format(' '.join(cmd), e.output.decode().rstrip()))# FIXME
            continue

        with open(acct_out, 'w') as fh:
            for line in res.decode():
                fh.write(line)


if __name__ == "__main__":
    produce_acct_logs(sys.argv[1])
