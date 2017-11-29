#!/usr/bin/env python3
"""{PIPELINE_NAME} pipeline (version: {PIPELINE_VERSION}): creates
pipeline-specific config files to given output directory and runs the
pipeline (unless otherwise requested).
"""
# generic usage {PIPELINE_NAME} and {PIPELINE_VERSION} replaced while
# printing usage

#--- standard library imports
#
import sys
import os
import logging

#--- third-party imports
#
import yaml

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from readunits import get_samples_and_readunits_from_cfgfile
from readunits import get_readunits_from_args
from pipelines import get_pipeline_version
from pipelines import PipelineHandler
from pipelines import logger as aux_logger
from pipelines import get_cluster_cfgfile
from pipelines import default_argparser
import configargparse


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2017 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# only dump() and following do not automatically create aliases
yaml.Dumper.ignore_aliases = lambda *args: True


PIPELINE_BASEDIR = os.path.dirname(sys.argv[0])
CFG_DIR = os.path.join(PIPELINE_BASEDIR, "cfg")


# same as folder name. also used for cluster job names
PIPELINE_NAME = "shotgun-metagenomics"

# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)


def main():
    """main function
    """

    default_parser = default_argparser(CFG_DIR,  with_readunits=True)
    parser = configargparse.ArgumentParser(description=__doc__.format(
        PIPELINE_NAME=PIPELINE_NAME, PIPELINE_VERSION=get_pipeline_version()),
                                     parents=[default_parser])

    parser._optionals.title = "Arguments"
    # pipeline specific args
    default = ['kraken', 'metaphlan2']
    parser.add_argument("-p", "--profilers", nargs='+', default=default,
                        help="Profilers to run (default = {}".format(", ".join(default)))
    parser.add_argument("--skip-srst2", action='store_true',
                        help="Skip SRST2")

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
    aux_logger.setLevel(logging.WARN + 10*args.quiet - 10*args.verbose)

    if os.path.exists(args.outdir):
        logger.fatal("Output directory %s already exists", args.outdir)
        sys.exit(1)

    # samples is a dictionary with sample names as key (mostly just
    # one) and readunit keys as value. readunits is a dict with
    # readunits (think: fastq pairs with attributes) as value
    if args.sample_cfg:
        if any([args.fq1, args.fq2, args.sample]):
            logger.fatal("Config file overrides fastq and sample arguments."
                         " Use one or the other")
            sys.exit(1)
        if not os.path.exists(args.sample_cfg):
            logger.fatal("Config file %s does not exist", args.sample_cfg)
            sys.exit(1)
        samples, readunits = get_samples_and_readunits_from_cfgfile(args.sample_cfg)

    else:# no sample config, so input is either fastq or existing bam
        samples = dict()

        if not args.sample:
            logger.fatal("Need sample name if not using config file")
            sys.exit(1)

        if args.fq1:
            readunits = get_readunits_from_args(args.fq1, args.fq2)
            # all readunits go into this one sample specified on the command-line
            samples[args.sample] = list(readunits.keys())

        else:
            logger.fatal("Need at least one fastq files as argument if not using config file")
            sys.exit(1)


    for ru in readunits.values():
        assert ru['fq2'], (
            "FastQ R2 missing, but pipelines requires paired-end reads")


    # turn arguments into cfg_dict (gets merged with other configs late)
    #
    cfg_dict = dict()
    cfg_dict['readunits'] = readunits
    cfg_dict['samples'] = samples
    cfg_dict['profilers'] = args.profilers
    cfg_dict['skip_srst2'] = args.skip_srst2
    pipeline_handler = PipelineHandler(
        PIPELINE_NAME, PIPELINE_BASEDIR,
        args, cfg_dict,
        cluster_cfgfile=get_cluster_cfgfile(CFG_DIR))
    pipeline_handler.setup_env()
    pipeline_handler.submit(args.no_run)


if __name__ == "__main__":
    main()
