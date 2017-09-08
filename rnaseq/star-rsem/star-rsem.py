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
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# only dump() and following do not automatically create aliases
yaml.Dumper.ignore_aliases = lambda *args: True


PIPELINE_BASEDIR = os.path.dirname(sys.argv[0])
CFG_DIR = os.path.join(PIPELINE_BASEDIR, "cfg")


# same as folder name. also used for cluster job names
PIPELINE_NAME = "star-rsem"

# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)


def main():
    """main function
    """

    default_parser = default_argparser(CFG_DIR, with_readunits=True)
    parser = configargparse.ArgumentParser(description=__doc__.format(
        PIPELINE_NAME=PIPELINE_NAME, PIPELINE_VERSION=get_pipeline_version()),
                                           parents=[default_parser])

    parser._optionals.title = "Arguments"
    # pipeline specific args
    parser.add_argument("--cuffdiff", action='store_true',
                        dest="run_cuffdiff",
                        help="Also run cuffdiff")
    choices = ["none", "forward", "reverse"]
    default = "none"
    parser.add_argument('--stranded', choices=choices, default=default,
                        help="Stranded library prep (default is {}; Following RSEM definition but see also"
                        " http://chipster.csc.fi/manual/library-type-summary.html)".format(default))
    parser.add_argument('--rsem-estimate-rspd', action='store_true',
                        help="Estimate read start position distribution in RSEM")
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
            logger.fatal("Config file overrides fastq and sample input arguments."
                         " Use one or the other")
            sys.exit(1)
        if not os.path.exists(args.sample_cfg):
            logger.fatal("Config file %s does not exist", args.sample_cfg)
            sys.exit(1)
        samples, readunits = get_samples_and_readunits_from_cfgfile(args.sample_cfg)
    else:
        if not all([args.fq1, args.sample]):
            logger.fatal("Need at least fq1 and sample without config file")
            sys.exit(1)

        readunits = get_readunits_from_args(args.fq1, args.fq2)
        # all readunits go into this one sample specified on the command-line
        samples = dict()
        samples[args.sample] = list(readunits.keys())

    # FIXME add checks on reffa index (currently not exposed via args)

    # turn arguments into cfg_dict that gets merged into pipeline config
    #
    cfg_dict = dict()
    cfg_dict['readunits'] = readunits
    cfg_dict['samples'] = samples
    if args.rsem_estimate_rspd:
        if 'rsem_extra_args' in cfg_dict:
            cfg_dict['rsem_extra_args'] += ' --estimate-rspd'
        else:
            cfg_dict['rsem_extra_args'] = '--estimate-rspd'
    cfg_dict['stranded'] = args.stranded
    cfg_dict['run_cuffdiff'] = args.run_cuffdiff
    cfg_dict['paired_end'] = any(ru.get('fq2') for ru in readunits.values())
    if cfg_dict['paired_end']:
        assert all(ru.get('fq2') for ru in readunits.values()), (
            "Can't handle mix of paired-end and single-end")

    pipeline_handler = PipelineHandler(
        PIPELINE_NAME, PIPELINE_BASEDIR,
        args, cfg_dict,
        cluster_cfgfile=get_cluster_cfgfile(CFG_DIR))
    pipeline_handler.setup_env()
    pipeline_handler.submit(args.no_run)


if __name__ == "__main__":
    main()
