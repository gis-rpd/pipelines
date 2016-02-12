#!/bin/env python3
"""Tests for SG10K pipeline
"""

import glob
import os
import tempfile
import sys
import subprocess
import shutil

PIPELINE_NAME = "SG10K"


# FIXME missing logger


def dry_run_test(basecmd, outdir):
    """Call wrapper with --no-run. Then execute pipeline with --dry-run
    """

    print("INFO: Dry-run test...")

    # call wrapper with no-run option
    #
    #print("DEBUG basecmd {}".format(basecmd))
    cmd = list(basecmd)
    cmd.extend(['-o', outdir, '--no-run'])
    try:
        res = subprocess.check_output(cmd)
    except subprocess.CalledProcessError:
        sys.stderr.write("FATAL: The following command failed: {}".format(' '.join(cmd)))
        raise
    print("INFO: Calling '{}' gave '{}'".format(' '.join(cmd), res.decode()))

    # then execute with dry-run option
    #
    curdir = os.getcwd()
    os.chdir(outdir)
    cmd = 'EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh'
    try:
        res = subprocess.check_output(cmd, shell=True)
    except subprocess.CalledProcessError:
        sys.stderr.write("FATAL: The following command failed: {}".format(' '.join(cmd)))
        raise
    print("INFO: Calling '{}' gave '{}'".format(' '.join(cmd), res.decode()))
    os.chdir(curdir)


def full_run_test(basecmd, outdir):
    """Run full test
    """

    print("INFO: Full run test...")

    # call wrapper with no-run option
    #
    #print("DEBUG basecmd {}".format(basecmd))
    cmd = list(basecmd)
    cmd.extend(['-o', outdir])
    try:
        res = subprocess.check_output(cmd)
    except subprocess.CalledProcessError:
        sys.stderr.write("FATAL: The following command failed: {}".format(' '.join(cmd)))
        raise
    print("INFO: Calling '{}' gave '{}'".format(' '.join(cmd), res.decode()))



def main():
    """main function
    """

    # FIXME missing useage
    
    wrapper = os.path.join(os.path.dirname(sys.argv[0]), "SG10K.py")
    #sys.path.insert(0, os.path.dirname(wrapper))
    from SG10K import SUBMISSIONLOG

    rpd_root = os.getenv('RPD_ROOT')
    assert rpd_root, ("Environment variable RPD_ROOT not defined")

    fastq_dir = os.path.join(rpd_root, "testing/data/SG10K/illumina-platinum-NA12878/")
    fastqs_1 = glob.glob(os.path.join(fastq_dir, "*ERR091571_1*1M-only.fastq.gz"))
    fastqs_2 = glob.glob(os.path.join(fastq_dir, "*ERR091571_2*1M-only.fastq.gz"))
    assert len(fastqs_1), ("No matches found in {}".format(fastq_dir))
    assert len(fastqs_1) == len(fastqs_2)


    basecmd = [wrapper]
    basecmd.append("-1")
    basecmd.extend(fastqs_1)
    basecmd.append("-2")
    basecmd.extend(fastqs_2)
    basecmd.extend(['--sample', '{}-test'.format(PIPELINE_NAME)])


    # dry run
    #
    outbasedir = os.path.join(rpd_root, "testing/output")
    outdir = tempfile.mkdtemp(prefix=PIPELINE_NAME + ".test", dir=outbasedir)
    os.rmdir(outdir)
    dry_run_test(basecmd, outdir)
    if os.path.isdir(outdir):
        shutil.rmtree(outdir)


    # full run
    #
    outbasedir = os.path.join(rpd_root, "testing/output")
    outdir = tempfile.mkdtemp(prefix=PIPELINE_NAME + ".test", dir=outbasedir)
    os.rmdir(outdir)
    full_run_test(basecmd, outdir)

    # FIXME following is site specific
    # FIXME to shared function
    with open(os.path.join(outdir, SUBMISSIONLOG)) as fh:
        line = fh.readline()
        assert line.startswith("Your job")
        jid = int(line.split()[2])
        sys.stderr.write("FIXME wait until jid {} done\n".format(jid))
    sys.stderr.write("FIXME how to check success? qacct on jid from submission log? would be site specific\n")
    sys.stderr.write("FIXME check at least mapping success\n")
    sys.stderr.write("FIXME delete outdir {} on success\n".format(outdir))
    if False:
        if os.path.isdir(outdir):
            shutil.rmtree(outdir)
    raise NotImplementedError


    sys.stderr.write("FIXME test snv performance on success\n")
    raise NotImplementedError

    sys.stderr.write("Test config file option\n")
    raise NotImplementedError


if __name__ == "__main__":
    sys.stderr.write("FIXME How to run automatically? qsub and wait for master?\n")
    main()
