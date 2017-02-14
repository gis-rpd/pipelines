#!/usr/bin/env python3
"""Stage data out
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
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from pipelines import DOWNSTREAM_OUTDIR_TEMPLATE
from pipelines import WORKFLOW_COMPLETION_FLAGFILE
from pipelines import is_devel_version
from config import site_cfg


# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)


STAGE_OUT_WORKER = os.path.abspath(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "stage_out.sh"))

S3_BUCKET = "s3://rpd-workflows-out"


def main():

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Increase verbosity")
    parser.add_argument('-q', '--quiet', action='count', default=0,
                        help="Decrease verbosity")
    args = parser.parse_args()

    # Repeateable -v and -q for setting logging level.
    # See https://www.reddit.com/r/Python/comments/3nctlm/what_python_tools_should_i_be_using_on_every/
    logger.setLevel(logging.WARN + 10*args.quiet - 10*args.verbose)

    # only makes sense for production if run as cron
    if is_devel_version():
        k = 'devel'
    else:
        k = 'production'
    basedir = site_cfg['downstream_outdir_base'][k]
    dirglob = DOWNSTREAM_OUTDIR_TEMPLATE.format(
        basedir=basedir, user="*", pipelineversion="*", pipelinename="*", timestamp="*")
    logger.debug("dirglob is %s", dirglob)

    for flagfile in glob.glob(os.path.join(
            dirglob, WORKFLOW_COMPLETION_FLAGFILE)):
        dir = os.path.abspath(os.path.dirname(flagfile))
        
        logger.info("Starting staging out of %s", dir)
        try:
            s3prefix = S3_BUCKET
            s3prefix = os.path.join(s3prefix, os.path.relpath(dir, basedir))
            cmd = [STAGE_OUT_WORKER, '-p', s3prefix, '-r', dir]
            _ = subprocess.check_output(cmd)
        except subprocess.CalledProcessError as e:
            logger.fatal("%s failed with exit code %s: %s. Will try to continue", 
                         ' '.join(cmd), e.returncode, e.output)
            continue


if __name__ == "__main__":
    main()
