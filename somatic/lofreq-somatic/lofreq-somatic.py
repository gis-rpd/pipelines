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
PIPELINE_NAME = "lofreq-somatic"

# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)



def main():
    """main function
    """

    default_parser = default_argparser(CFG_DIR)
    parser = configargparse.ArgumentParser(description=__doc__.format(
        PIPELINE_NAME=PIPELINE_NAME, PIPELINE_VERSION=get_pipeline_version()),
                                     parents=[default_parser])

    parser._optionals.title = "Arguments"
    # pipeline specific args
    parser.add_argument("--normal-fq1", nargs="+",
                        help="Normal FastQ file/s (gzip only)."
                        " Multiple input files supported (auto-sorted)."
                        " Note: each file (or pair) gets a unique read-group id."
                        " Collides with --sample-cfg.")
    parser.add_argument('--normal-fq2', nargs="+",
                        help="Normal FastQ file/s (if paired) (gzip only). See also --fq1")
    parser.add_argument("--tumor-fq1", nargs="+",
                        help="Tumor FastQ file/s (gzip only)."
                        " Multiple input files supported (auto-sorted)."
                        " Note: each file (or pair) gets a unique read-group id."
                        " Collides with --sample-cfg.")
    parser.add_argument('--tumor-fq2', nargs="+",
                        help="Tumor FastQ file/s (if paired) (gzip only). See also --fq1")
    parser.add_argument('-t', "--seqtype", required=True,
                        choices=['WGS', 'WES', 'targeted'],
                        help="Sequencing type")
    parser.add_argument('-l', "--bed",
                        help="Bed file listing regions of interest."
                        " Required for WES and targeted sequencing.")
    parser.add_argument('-D', '--dont-mark-dups', action='store_true',
                        help="Don't mark duplicate reads")
    parser.add_argument('--normal-bam',
                        help="Advanced: Injects normal BAM (overwrites normal-fq options)."
                        " WARNING: reference and postprocessing need to match pipeline requirements")
    parser.add_argument('--tumor-bam',
                        help="Advanced: Injects tumor BAM (overwrites tumor-fq options)."
                        " WARNING: reference and postprocessing need to match pipeline requirements")


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
        if any([args.normal_fq1, args.normal_fq2, args.tumor_fq1, args.tumor_fq2,
                args.normal_bam, args.tumor_bam]):
            logger.fatal("Config file overrides fastq and sample input arguments."
                         " Use one or the other")
            sys.exit(1)
        if not os.path.exists(args.sample_cfg):
            logger.fatal("Config file %s does not exist", args.sample_cfg)
            sys.exit(1)
        samples, readunits = get_samples_and_readunits_from_cfgfile(args.sample_cfg)
    else:
        samples = dict()

        if args.normal_bam:
            normal_readunits = dict()
            samples["normal"] = []
            assert os.path.exists(args.normal_bam)
        else:
            if not all([args.normal_fq1, args.tumor_fq1]):
                logger.fatal("Need at least fq1 and sample without config file")
                sys.exit(1)
            normal_readunits = get_readunits_from_args(args.normal_fq1, args.normal_fq2)
            samples["normal"] = list(normal_readunits.keys())

        if args.tumor_bam:
            tumor_readunits = dict()
            samples["tumor"] = []
            assert os.path.exists(args.tumor_bam)
        else:
            tumor_readunits = get_readunits_from_args(args.tumor_fq1, args.tumor_fq2)
            samples["tumor"] = list(tumor_readunits.keys())

        readunits = dict(normal_readunits)
        readunits.update(tumor_readunits)

    assert sorted(samples) == sorted(["normal", "tumor"])

    # FIXME howt to
    # if not os.path.exists(reffa):
    #    logger.fatal("Reference '%s' doesn't exist", reffa)
    #    sys.exit(1)
    #
    #for p in ['bwa', 'samtools']:
    #    if not ref_is_indexed(reffa, p):
    #        logger.fatal("Reference '%s' doesn't appear to be indexed with %s", reffa, p)
    #        sys.exit(1)

    if args.seqtype in ['WES', 'targeted']:
        if not args.bed:
            logger.fatal("Analysis of exome and targeted sequence runs requires a bed file")
            sys.exit(1)
        else:
            if not os.path.exists(args.bed):
                logger.fatal("Bed file %s does not exist", args.sample_cfg)
                sys.exit(1)
            logger.warning("Compatilibity between bed file and"
                           " reference not checked")# FIXME

    # turn arguments into cfg_dict that gets merged into pipeline config
    #
    cfg_dict = dict()
    cfg_dict['readunits'] = readunits
    cfg_dict['samples'] = samples

    cfg_dict['seqtype'] = args.seqtype
    cfg_dict['intervals'] = os.path.abspath(args.bed) if args.bed else None
    cfg_dict['mark_dups'] = not args.dont_mark_dups

    pipeline_handler = PipelineHandler(
        PIPELINE_NAME, PIPELINE_BASEDIR,
        args, cfg_dict,
        cluster_cfgfile=get_cluster_cfgfile(CFG_DIR))

    pipeline_handler.setup_env()

    # inject existing BAM by symlinking (everything upstream is temporary anyway)
    for sample, bam in [("normal", args.normal_bam),
                        ("tumor", args.tumor_bam)]:
        if bam:
            # target as defined in Snakefile!
            target = os.path.join(args.outdir, "out", sample,
                                  "{}.bwamem.lofreq.dedup.lacer.bam".format(sample))
            os.makedirs(os.path.dirname(target))
            os.symlink(os.path.abspath(bam), target)

    pipeline_handler.submit(args.no_run)


if __name__ == "__main__":
    main()
