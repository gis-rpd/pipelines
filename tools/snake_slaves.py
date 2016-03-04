#!/usr/bin/env python3
"""Check snakemake's slave cluster jobs for a certain run
"""


#--- standard library imports
#
import sys
import os
import argparse
import logging
import shlex
import glob
import subprocess

#--- third-party imports
#/

#--- project specific imports
#/

# master log relative to outdir
#MASTERLOG = os.path.join(LOG_DIR_REL, "snakemake.log".format(PIPELINE_NAME))
#SUBMISSIONLOG = os.path.join(LOG_DIR_REL, "submission.log".format(PIPELINE_NAME))

# global logger
LOG = logging.getLogger()


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
    parser.add_argument('-l', '--list', action="store_true",
                        help="list jids")
    parser.add_argument('-c', '--cmd',
                        help="Run command for each jid. Use {jid} as placeholder,"
                        " e.g. qstat -j {jid}")
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

    if args.cmd:
        assert '{jid}' in args.cmd

    cluster_logfiles = glob.glob(os.path.join(args.logdir, "*.sh.o*[0-9]"))
    if len(cluster_logfiles) == 0:
        LOG.warn("No matching cluster log files found in {}".format(args.logdir))
        sys.exit(1)
    LOG.info("Found {} cluster log files".format(len(cluster_logfiles)))

    jids = [jid_from_cluster_logfile(f) for f in cluster_logfiles]

    for j in jids:
        if args.list:
            print(j)

        if args.cmd:
            cmd = args.cmd.format(jid=j)
            try:
                res = subprocess.check_output(shlex.split(cmd))#, stderr=subprocess.STDOUT)
                print(res)
            except subprocess.CalledProcessError:
                #LOG.error("The following command failed: {}".format(cmd))
                # stderr already printed 
                pass



if __name__ == "__main__":
    main()
