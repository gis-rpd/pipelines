#!/usr/bin/env python3
"""Write a sample config file (e.g. sample.yaml; useful for pipeline input) for a given directory containing fastq files
"""

#--- standard library imports
#
import os
import sys
import argparse
import logging

#--- third-party imports
#
#/

# --- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(os.path.join(os.path.dirname(
    os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from readunits import sampledir_to_cfg


__author__ = "Andreas WILM"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)


def main():
    """main function"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-s', "--sampledir", required=True,
                        help="Sample directory containing fastq files (following preconfigured naming conventions)")
    parser.add_argument('-o', "--samplecfg", required=True,
                        help="Output YAML files. FastQ file names will be relative to this file")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Increase verbosity")
    parser.add_argument('-f', '--flowcell-id',
                        help="Flowcell ID (can't be guessed usually)")
    parser.add_argument('-r', '--run-id',
                        help="Run ID (can't be guessed usually")
    parser.add_argument('-q', '--quiet', action='count', default=0,
                        help="Decrease verbosity")
    parser.add_argument('--novogene', action='store_true',
                        help="Use NovogeneAIT naming scheme")
    args = parser.parse_args()

    # Repeateable -v and -q for setting logging level.
    # See https://www.reddit.com/r/Python/comments/3nctlm/what_python_tools_should_i_be_using_on_every/
    logger.setLevel(logging.WARN + 10*args.quiet - 10*args.verbose)

    if not os.path.exists(args.sampledir):
        logger.fatal("Non existing sample directory %s", args.sampledir)
        sys.exit(1)
    if os.path.exists(args.samplecfg):
        logger.fatal("Cowardly refusing to overwrite existing %s", args.samplecfg)
        sys.exit(1)


    sampledir_to_cfg(args.sampledir, args.samplecfg,
                     run_id=args.run_id, flowcell_id=args.flowcell_id,
                     novogene=args.novogene)


if __name__ == "__main__":
    main()
