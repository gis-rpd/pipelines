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
from collections import deque

#--- third-party imports
#/

#--- project specific imports
#/

# master log relative to outdir
MASTERLOG = "snakemake.log"
SUBMISSIONLOG = "submission.log"

# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)


class JIDStatus(object):

    def __init__(self, jid, scheduler="UGE", logdir=None):
        self.jid = jid
        assert scheduler in ["UGE", "PBS"]

        self.scheduler = scheduler
        self.logdir = logdir
        self.is_running = None
        self.exit_status = None
        self.get_status()

        
    def get_status(self):
        if self.scheduler == "PBS":
            cmd = ['qstat', self.jid]
        elif self.scheduler == "UGE":
            cmd = ['qstat', '-j', self.jid]
        else:
            raise ValueError(self.scheduler)

        try:
            res = subprocess.check_output(cmd, stderr=subprocess.STDOUT)

        except subprocess.CalledProcessError as e:
            if self.scheduler == "PBS":
                assert 'Unknown Job Id' in e.output.decode()
                self.is_running = False
                if self.logdir:
                    logm = glob.glob(os.path.join(self.logdir, self.jid + "*" + ".OU"))
                    assert len(logm) == 1, (
                        "No log files found for jid {} in {}".format(self.jid, self.logdir))
                    with open(logm[0]) as fh:
                        for line in fh:
                            if 'Exit Status:' in line:
                                self.exit_status = int(line.strip().split(":")[-1])
                                break
                if self.exit_status is None:
                    raise ValueError(res.decode())

            elif self.scheduler == "UGE":
                assert 'not exist' in e.output.decode(), (e.output.decode())
                self.is_running = False
                cmd = ['qacct', '-j', self.jid]
                res = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
                for line in res.decode().splitlines():
                    #print("DEBUG line={}".format(line))
                    if line.startswith("exit_status"):
                        self.exit_status = int(line[len("exit_status"):].strip())
                        break
                if self.exit_status is None:
                    raise ValueError(res.decode())
        else:
            self.is_running = True

        #print("DEBUG: jid={} is_running={} exit_status={}".format(self.jid, self.is_running, self.exit_status))


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
        scheduler = "UGE"
    else:
        if 'PBSPro' in res.decode():
            scheduler = "PBS"
        else:
            raise ValueError(res.decode())

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dir', nargs=1,
                        help="Analysis directory (output dir of pipeline wrapper)")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Increase verbosity")
    parser.add_argument('-q', '--quiet', action='count', default=0,
                        help="Decrease verbosity")
    args = parser.parse_args()

    # Repeateable -v and -q for setting logging level.
    # See https://www.reddit.com/r/Python/comments/3nctlm/what_python_tools_should_i_be_using_on_every/
    # and https://gist.github.com/andreas-wilm/b6031a84a33e652680d4
    # script -vv -> DEBUG
    # script -v -> INFO
    # script -> WARNING
    # script -q -> ERROR
    # script -qq -> CRITICAL
    # script -qqq -> no logging at all
    logger.setLevel(logging.WARN + 10*args.quiet - 10*args.verbose)

    pipedir = args.dir[0]
    if not os.path.exists(pipedir):
        logger.fatal("Log directory %s doesn't exist", pipedir)
        sys.exit(1)
    logdir = os.path.join(pipedir, 'logs')
    if not os.path.exists(logdir):
        logger.fatal("Couldn't find expected log directory in %s", pipedir)
        sys.exit(1)


    # Analyze submission log
    #
    submissionlog = os.path.join(logdir, SUBMISSIONLOG)
    if not os.path.exists(submissionlog):
        logger.warning("Submission logfile %s not found: job not submitted", submissionlog)
    else:
        print("Analyzing submission logfile %s" % submissionlog)
        with open(submissionlog) as fh:
            master_jid = []
            # only use last one
            for line in fh:
                line = line.rstrip()
                if scheduler == "PBS":
                    jid = line.strip()
                elif scheduler == "UGE":
                    assert line.startswith("Your job") and line.endswith("has been submitted")
                    jid = line.split()[2]
                else:
                    raise ValueError(scheduler)
                    
            jid_status = JIDStatus(jid, scheduler=scheduler, logdir=logdir)
            if jid_status.is_running:
                print("Master {} still running. Exiting...".format(jid))
                return# exit
            else:
                print("Master {} not running.".format(jid))

    # analyzing masterlog/snakemake.log
    #
    masterlog = os.path.join(logdir, MASTERLOG)
    if not os.path.exists(masterlog):
        logger.warning("Master logfile %s not found: job not (yet) running (might be in queue). Exiting...", masterlog)
        return# exit
    print("\nAnalyzing master logfile %s" % submissionlog)
    workflow_done = False
    last_lines = deque(maxlen=10)    
    with open(masterlog) as fh:
        for line in fh:
            line = line.rstrip()
            last_lines.append(line)
            if line.startswith("["):
                if 'steps (100%) done' in line or "Nothing to be done" in line:
                    print("Workflow completed: {}".format(line))
                    return# exit
                
    workflow_failed = False
    for line in last_lines:
        # snakemake 4.1
        if "Exiting because a job execution failed" in line:
            print("Workflow execution failed")
            workflow_failed = True
    if not workflow_failed:
        print("Workflow execution still ongoing")
        return# exit

    print("\nLet's look at the worker job (in chronological order)")
    abnormal_fail = False
    with open(masterlog) as fh:
        for line in fh:
            line = line.rstrip()
            # snakemake 4.1 with drmaa
            if "Submitted DRMAA job" in line and "with external jobid" in line:
                jid = line.strip().split()[-1].strip(".")
                jid_status = JIDStatus(jid, scheduler=scheduler, logdir=logdir)
                #print("DEBUG: {}".format(jid_status))
                if jid_status.is_running:
                    print("Worker {}: running".format(jid))
                elif jid_status.exit_status == 0:
                    print("Worker {}: completed successfully".format(jid))
                elif jid_status.exit_status == 1:
                    print("Worker {}: FAILED".format(jid))
                elif jid_status.exit_status > 1:
                    print("Worker {}: FAILED ABNORMALLY with status {}. Check runtime and memory limits".format(jid, jid_status.exit_status))
                    abnormal_fail = True
    print()
    if abnormal_fail:
        print("Check and adjust runtime and memory limits before resubmitting")
    else:
        print("A simple resubmission should work (For GIS: cd %s && qsub run.sh >> logs/submission.log)" % pipedir)

            
if __name__ == "__main__":
    main()
