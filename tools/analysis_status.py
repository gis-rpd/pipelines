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
LOG = logging.getLogger()


def jid_is_running(jid):
    try:
        cmd = ['qstat', '-j', jid]
        _res = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return True
    except subprocess.CalledProcessError as e:
        assert "Following jobs do not exist" in e.output.decode(), (e.output.decode())
        # otherwise communication error?
        return False


def jid_from_cluster_logfile(logfile):
    """extract jid from cluster log file"""
    jid = ""
    for pref in ["sh.o", "sh.e"]:
        if pref in logfile:
            try:
                jid = logfile[logfile.index(pref)+len(pref):]
            except ValueError:
                pass
            else:
                break
    if len(jid) == 0:
        raise ValueError(logfile)
    return jid


def main():
    """main function
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-d', "--logdir",
                        help="Log directory in run folder (usually runfolder/logs/)",
                        required=True)
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-q', '--quiet', action='count', default=0)

    args = parser.parse_args()

    # Repeateable -v and -q for setting logging level.
    # See https://gist.github.com/andreas-wilm/b6031a84a33e652680d4
    logging_level = logging.WARN + 10*args.quiet - 10*args.verbose
    logging.basicConfig(level=logging_level,
                        format='%(levelname)s [%(asctime)s]: %(message)s')


    if not os.path.exists(args.logdir):
        LOG.fatal("Log directory {} doesn't exist".format(args.logdir))
        sys.exit(1)


    cluster_logfiles = glob.glob(os.path.join(args.logdir, "*.sh.o*[0-9]"))
    print("Found {} slaves (cluster log files)".format(len(cluster_logfiles)))
    slave_jids = [jid_from_cluster_logfile(f) for f in cluster_logfiles]
    for jid in slave_jids:
        if jid_is_running(jid):
            print("Slave jid {} still running (status?)".format(jid))# FIXME
        else:
            print("Slave jid {} not running (anymore).".format(jid))


    submissionlog = os.path.join(args.logdir, SUBMISSIONLOG)
    if not os.path.exists(submissionlog):
        LOG.warn("Submission logfile {} not found: job not submitted".format(submissionlog))
    else:
        with open(submissionlog) as fh:
            for line in fh:
                line = line.rstrip()
                if line.startswith("Your job") and line.endswith("has been submitted"):
                    jid = line.split()[2]
                    if jid_is_running(jid):
                        print("Master jid {} still running (status?)".format(jid))# FIXME
                    else:
                        print("Master jid {} not running (anymore).".format(jid))


    masterlog = os.path.join(args.logdir, MASTERLOG)
    if not os.path.exists(masterlog):
        LOG.warn("Master logfile {} not found: job not (yet) running (might be in queue)".format(masterlog))
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
