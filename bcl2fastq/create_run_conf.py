#!/usr/bin/env python3
"""Generates conf.yaml under Run directory
"""

#--- standard library imports
#
import sys
import os
import logging
import argparse

# third party imports
#
import yaml

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from bcl2fastq import get_mux_units_from_cfgfile

__author__ = "Lavanya Veeravalli"
__email__ = "veeravallil@gis.a-star.edu.sg"
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
    parser.add_argument("-b", "--bcl2fastq", required=True,
                        help="bcl2fastq directory")
    parser.add_argument('-f', "--overwrite", action='store_true',
                        help="Overwrite existing files")
    parser.add_argument('-n', "--dry-run", action='store_true',
                        help="Dry run")
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
    # script -qqq -> no loggerging at all
    logger.setLevel(logging.WARN + 10*args.quiet - 10*args.verbose)

    if not os.path.exists(args.bcl2fastq):
        logger.fatal("bcl2fastq %s does not exist", args.bcl2fastq)
        sys.exit(1)
    logger.info("bcl2fastq is %s", args.bcl2fastq)
    muxinfo_cfg = os.path.join(args.bcl2fastq + '/muxinfo.yaml')
    if not os.path.exists(muxinfo_cfg):
        logger.fatal("muxinfo.yaml '%s' does not exist under Run directory.\n", args.bcl2fastq)
        sys.exit(1)
    mux_units = get_mux_units_from_cfgfile(muxinfo_cfg)
    user_data = dict()
    for mu in mux_units:
        k = mu.mux_dir
        run_num = mu.run_id + "_" + mu.flowcell_id
        mu_dict = dict(mu._asdict())
        user_data[k] = mu_dict
    conf = os.path.join(args.bcl2fastq + '/conf.yaml')
    if args.dry_run:
        logger.warning("Skipped creation of %s", conf)
    else:
        if os.path.exists(conf) and not args.overwrite:
            logger.fatal("Refusing to overwrite existing file %s", conf)
            sys.exit(1)
        with open(conf, 'w') as fh:
            fh.write(yaml.dump(dict(units=user_data), default_flow_style=False))
            fh.write(yaml.dump(dict(run_num=run_num), default_flow_style=False))

if __name__ == "__main__":
    main()
    logger.info("Successful program exit")
