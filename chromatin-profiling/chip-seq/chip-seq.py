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
import argparse
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
from pipelines import get_default_queue
from pipelines import email_for_user


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# only dump() and following do not automatically create aliases
yaml.Dumper.ignore_aliases = lambda *args: True


PIPELINE_BASEDIR = os.path.dirname(sys.argv[0])
CFG_DIR = os.path.join(PIPELINE_BASEDIR, "cfg")

# same as folder name. also used for cluster job names
PIPELINE_NAME = "chip-seq"

MARK_DUPS = True

# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)


def main():
    """main function
    """

    parser = argparse.ArgumentParser(description=__doc__.format(
        PIPELINE_NAME=PIPELINE_NAME, PIPELINE_VERSION=get_pipeline_version()))

    # generic args
    parser.add_argument('-o', "--outdir", required=True,
                        help="Output directory (must not exist)")
    parser.add_argument('--name',
                        help="Give this analysis run a name (used in email and report)")
    parser.add_argument('--no-mail', action='store_true',
                        help="Don't send mail on completion")
    default = email_for_user()
    parser.add_argument('--mail', dest='mail_address', default=default,
                        help="Send completion emails to this address (default: {})".format(default))
    default = get_default_queue('slave')
    parser.add_argument('-w', '--slave-q', default=default,
                        help="Queue to use for slave jobs (default: {})".format(default))
    default = get_default_queue('master')
    parser.add_argument('-m', '--master-q', default=default,
                        help="Queue to use for master job (default: {})".format(default))
    parser.add_argument('-n', '--no-run', action='store_true')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Increase verbosity")
    parser.add_argument('-q', '--quiet', action='count', default=0,
                        help="Decrease verbosity")
    cfg_group = parser.add_argument_group('Configuration files (advanced)')
    cfg_group.add_argument('--sample-cfg',
                           help="Config-file (YAML) listing samples and readunits."
                           " Collides with -1, -2 and -s")
    for name, descr in [("references", "reference sequences"),
                        ("params", "parameters"),
                        ("modules", "modules")]:
        default = os.path.abspath(os.path.join(CFG_DIR, "{}.yaml".format(name)))
        cfg_group.add_argument('--{}-cfg'.format(name),
                               default=default,
                               help="Config-file (yaml) for {}. (default: {})".format(descr, default))

    # pipeline specific args
    parser.add_argument("--control-fq1", nargs="+",
                        help="Control FastQ file/s (gzip only)."
                        " Multiple input files supported (auto-sorted)."
                        " Note: each file (or pair) gets a unique read-group id."
                        " Collides with --sample-cfg.")
    parser.add_argument('--control-fq2', nargs="+",
                        help="Control FastQ file/s (if paired) (gzip only). See also --fq1")
    parser.add_argument("--treatment-fq1", nargs="+",
                        help="Treatment FastQ file/s (gzip only)."
                        " Multiple input files supported (auto-sorted)."
                        " Note: each file (or pair) gets a unique read-group id."
                        " Collides with --sample-cfg.")
    parser.add_argument('--treatment-fq2', nargs="+",
                        help="Treatment FastQ file/s (if paired) (gzip only). See also --fq1")
    parser.add_argument('--control-bam',
                        help="Advanced: Injects control BAM (overwrites control-fq options)."
                        " WARNING: reference and postprocessing need to match pipeline requirements")
    parser.add_argument('--treatment-bam',
                        help="Advanced: Injects treatment BAM (overwrites treatment-fq options)."
                        " WARNING: reference and postprocessing need to match pipeline requirements")
    choices = ['bwa-aln', 'bwa-mem']
    default = choices[0]
    parser.add_argument('--mapper', default=default, choices=choices,
                        help="Mapper to use. One of {}. Default {}".format(",".join(choices), default))
    
    choices = ['TF', 'histone-narrow', 'histone-broad']#, 'open-chromatin']
    parser.add_argument('-t', '--peak-type', required=True, choices=choices,
                        help="Peak type. One of {}".format(",".join(choices)))
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
        if any([args.control_fq1, args.control_fq2, args.treatment_fq1, args.treatment_fq2,
                args.control_bam, args.treatment_bam]):
            logger.fatal("Config file overrides fastq and sample input arguments."
                         " Use one or the other")
            sys.exit(1)
            if not os.path.exists(args.sample_cfg):
                logger.fatal("Config file %s does not exist", args.sample_cfg)
                sys.exit(1)
        samples, readunits = get_samples_and_readunits_from_cfgfile(args.sample_cfg)
    else:
        samples = dict()

        if args.control_bam:
            control_readunits = dict()
            samples["control"] = []
            assert os.path.exists(args.control_bam)
        else:
            if not all([args.control_fq1, args.treatment_fq1]):
                logger.fatal("Need at least fq1 and sample without config file")
                sys.exit(1)
            control_readunits = get_readunits_from_args(args.control_fq1, args.control_fq2)
            samples["control"] = list(control_readunits.keys())

        if args.treatment_bam:
            treatment_readunits = dict()
            samples["treatment"] = []
            assert os.path.exists(args.treatment_bam)
        else:
            treatment_readunits = get_readunits_from_args(args.treatment_fq1, args.treatment_fq2)
            samples["treatment"] = list(treatment_readunits.keys())

        readunits = dict(control_readunits)
        readunits.update(treatment_readunits)

    assert sorted(samples) == sorted(["control", "treatment"])


    # turn arguments into user_data that gets merged into pipeline config
    #
    # generic data first
    user_data = dict()
    user_data['mail_on_completion'] = not args.no_mail
    user_data['mail_address'] = args.mail_address
    user_data['readunits'] = readunits
    user_data['samples'] = samples
    if args.name:
        user_data['analysis_name'] = args.name

    # either paired end or not, but no mix allows
    if all([ru.get('fq2') for ru in readunits.values()]):
        user_data['paired_end'] = True
    elif not any([ru.get('fq2') for ru in readunits.values()]):
        user_data['paired_end'] = False
    else:
        logger.fatal("Mixed paired-end and single-end not allowed")
        sys.exit(1)
    logger.critical("Fixed genomesize. Should be 80%% of input")
    user_data['peak_type'] = args.peak_type
    user_data['mapper'] = args.mapper

    pipeline_handler = PipelineHandler(
        PIPELINE_NAME, PIPELINE_BASEDIR,
        args.outdir, user_data,
        master_q=args.master_q,
        slave_q=args.slave_q,
        params_cfgfile=args.params_cfg,
        modules_cfgfile=args.modules_cfg,
        refs_cfgfile=args.references_cfg,
        cluster_cfgfile=get_cluster_cfgfile(CFG_DIR))
    pipeline_handler.setup_env()
    logger.critical("No BAM injection")
    pipeline_handler.submit(args.no_run)


if __name__ == "__main__":
    main()
