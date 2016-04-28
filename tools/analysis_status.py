#!/usr/bin/env python3
"""Check snakemake's slave cluster jobs for a certain run
"""


#--- standard library imports
#
import sys
import os
import argparse
import logging
import glob
import subprocess

#--- third-party imports
#/

#--- project specific imports
#/

# master log relative to outdir
MASTERLOG = "snakemake.log"
SUBMISSIONLOG = "submission.log"

# global logger
LOG = logging.getLogger(__name__)



def jid_is_running(jid, is_pbspro):
    """run qstat to find out whether jid is still running
    """
    if is_pbspro:
        cmd = ['qstat', jid]
    else:
        cmd = ['qstat', '-j', jid]
    try:
        _ = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return True
    except subprocess.CalledProcessError as e:
        if is_pbspro:
            # Unknown Job Id happens on log rotation.
            if not any(['Unknown Job Id' in x for x in [e.output.decode(), e.output.decode()]]):
                assert any(['has finished' in x for x in [e.output.decode(), e.output.decode()]])
        else:
            assert any(["Following jobs do not exist" in x for x in [e.output.decode(), e.output.decode()]])
            # otherwise communication error?
            return False


def jid_from_cluster_logfile(logfile):
    """extract jid from cluster log file"""
    jid = ""
    # PBS Pro
    if logfile.endswith(".OU") or logfile.endswith(".ER"):
        jid = os.path.basename(logfile[:-3])
    # LSF
    elif "sh.o" in logfile or "sh.e" in logfile:
        for pref in ["sh.o", "sh.e"]:
            try:
                jid = logfile[logfile.index(pref)+len(pref):]
            except ValueError:
                pass
            else:
                break
    else:
        raise ValueError(logfile)
    if len(jid) == 0:
        raise ValueError(logfile)
    return jid


def main():
    """main function
    """

    # should atually check first if we run qstat at all
    try:
        res = subprocess.check_output(['qstat', '--version'], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        is_pbspro = False
    else:
        if 'PBSPro' in res.decode():
            is_pbspro = True
        else:
            raise ValueError(res.decode())

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dir', nargs=1,
                        help="Analysis directory (output dir of pipeline wrapper)")
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-q', '--quiet', action='count', default=0)

    args = parser.parse_args()

    # Repeateable -v and -q for setting logging level.
    # See https://gist.github.com/andreas-wilm/b6031a84a33e652680d4
    logging_level = logging.WARN + 10*args.quiet - 10*args.verbose
    logging.basicConfig(level=logging_level,
                        format='%(asctime)s - %(filename)s - %(levelname)s - %(message)s')


    if not os.path.exists(args.dir[0]):
        LOG.fatal("Log directory {} doesn't exist".format(args.dir[0]))
        sys.exit(1)
    logdir = os.path.join(args.dir[0], 'logs')
    if not os.path.exists(logdir):
        LOG.fatal("Couldn't find expected log directory in {}".format(args.dir[0]))
        sys.exit(1)


    cluster_logfiles = []
    # LFS
    cluster_logfiles.extend(glob.glob(os.path.join(logdir, "*.sh.o*[0-9]")))
    # PBS Pro
    cluster_logfiles.extend(glob.glob(os.path.join(logdir, "*OU")))
    print("Found {} slaves (cluster log files)".format(len(cluster_logfiles)))
    slave_jids = [jid_from_cluster_logfile(f) for f in cluster_logfiles]
    for jid in slave_jids:
        if jid_is_running(jid, is_pbspro):
            print("Slave jid {} still running (status?)".format(jid))# FIXME
        else:
            print("Slave jid {} not running (anymore).".format(jid))


    submissionlog = os.path.join(logdir, SUBMISSIONLOG)
    if not os.path.exists(submissionlog):
        LOG.warning("Submission logfile {} not found: job not submitted".format(submissionlog))
    else:
        with open(submissionlog) as fh:
            for line in fh:
                line = line.rstrip()
                if is_pbspro:
                    jid = line.strip()
                    if jid_is_running(jid, is_pbspro):
                        print("Master jid {} still running (status?)".format(jid))# FIXME
                    else:
                        print("Master jid {} not running (anymore).".format(jid))

                elif line.startswith("Your job") and line.endswith("has been submitted"):
                    jid = line.split()[2]
                    if jid_is_running(jid, is_pbspro):
                        print("Master jid {} still running (status?)".format(jid))# FIXME
                    else:
                        print("Master jid {} not running (anymore).".format(jid))
                else:
                    raise ValueError(line)


    masterlog = os.path.join(logdir, MASTERLOG)
    if not os.path.exists(masterlog):
        LOG.warning("Master logfile {} not found: job not (yet) running (might be in queue)".format(masterlog))
    else:
        workflow_done = False
        with open(masterlog) as fh:
            for line in fh:
                line = line.rstrip()
                if line.startswith("["):
                    if 'steps (100%) done' in line or "Nothing to be done" in line:
                        print("Workflow completed: {}".format(line))
                        workflow_done = True
        if not workflow_done:
            print("Workflow not complete")


if __name__ == "__main__":
    main()
