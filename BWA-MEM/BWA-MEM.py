#!/usr/bin/env python3
"""{PIPELINE_NAME} pipeline (version: {PIPELINE_VERSION}): creates
pipeline-specific config files to given output directory and runs the
pipeline (unless otherwise requested).
"""
# generic useage {PIPELINE_NAME} and {PIPELINE_VERSION} replaced while
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
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from pipelines import get_pipeline_version, get_site
from pipelines import write_dk_init, write_snakemake_init
from pipelines import write_snakemake_env, write_cluster_config
from pipelines import write_merged_usr_and_default_cfg, write_run_template_and_exec
from pipelines import ref_is_indexed
from pipelines import logger as aux_logger
from pipelines import LOG_DIR_REL, MASTERLOG, RC_FILES
from readunits import get_reads_unit_from_cfgfile, get_reads_unit_from_args, key_for_read_unit


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# only dump() and following do not automatically create aliases
yaml.Dumper.ignore_aliases = lambda *args: True


BASEDIR = os.path.dirname(sys.argv[0])

# same as folder name. also used for cluster job names
PIPELINE_NAME = "BWA-MEM"


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
    parser.add_argument('-1', "--fq1", nargs="+",
                        help="FastQ file/s (gzip only)."
                        " Multiple input files supported (auto-sorted)."
                        " Note: each file gets a unique read group id assigned."
                        " Collides with -c.")
    parser.add_argument('-2', "--fq2", nargs="+",
                        help="FastQ file/s (if paired) (gzip only). See also --fq1")
    parser.add_argument('-s', "--sample", required=True,
                        help="Sample name")
    parser.add_argument('-r', "--reffa", required=True,
                        help="Reference fasta file to use. Needs to be indexed already (bwa index)")
    parser.add_argument('-d', '--mark-dups', action='store_true',
                        help="Mark duplicate reads")
    parser.add_argument('-c', "--config",
                        help="Config file (YAML) listing: run-, flowcell-, sample-id, lane"
                        " as well as fastq1 and fastq2 per line. Will create a new RG per line,"
                        " unless read groups is set in last column. Collides with -1, -2")
    parser.add_argument('-o', "--outdir", required=True,
                        help="Output directory (may not exist)")
    parser.add_argument('--no-mail', action='store_true',
                        help="Don't send mail on completion")
    parser.add_argument('-w', '--slave-q',
                        help="Queue to use for slave jobs")
    parser.add_argument('-m', '--master-q',
                        help="Queue to use for master job")
    parser.add_argument('-n', '--no-run', action='store_true')
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-q', '--quiet', action='count', default=0)

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

    if not os.path.exists(args.reffa):
        logger.fatal("Reference '%s' doesn't appear to be indexed", args.reffa)
        sys.exit(1)
    if not ref_is_indexed(args.reffa, "bwa"):
        logger.fatal("Reference '%s' doesn't appear to be indexed", args.reffa)
        sys.exit(1)

    if args.config:
        if any([args.fq1, args.fq2]):
            logger.fatal("Config file overrides fastq input arguments. Use one or the other")
            sys.exit(1)
        if not os.path.exists(args.config):
            logger.fatal("Config file %s does not exist", args.config)
            sys.exit(1)
        read_units = get_reads_unit_from_cfgfile(args.config)
    else:
        read_units = get_reads_unit_from_args(args.fq1, args.fq2)

    for i, ru in enumerate(read_units):
        logger.debug("Checking read unit #%d: %s", i, ru)
        for f in [ru.fq1, ru.fq2]:
            if f and not os.path.exists(f):
                logger.fatal("Non-existing input file %s", f)
                sys.exit(1)

    if os.path.exists(args.outdir):
        logger.fatal("Output directory %s already exists", args.outdir)
        sys.exit(1)
    # also create log dir immediately
    logger.info("Creating output directory %s", args.outdir)
    os.makedirs(os.path.join(args.outdir, LOG_DIR_REL))


    # turn arguments into user_data that gets merged into pipeline config
    user_data = {'mail_on_completion': not args.no_mail}
    user_data['readunits'] = dict()
    for ru in read_units:
        k = key_for_read_unit(ru)
        user_data['readunits'][k] = dict(ru._asdict())
    user_data['references'] = {'genome' : args.reffa}
    user_data['mark_dups'] = args.mark_dups

    # samples is a dictionary with sample names as key (here just one)
    # each value is a list of readunits
    user_data['samples'] = dict()
    user_data['samples'][args.sample] = list(user_data['readunits'].keys())


    try:
        site = get_site()
    except ValueError:
        logger.warning("Unknown site")
        site = "NA"
    elm_data = {'pipeline_name': PIPELINE_NAME,
                'pipeline_version': get_pipeline_version(),
                'site': site,
                'instance_id': 'SET_ON_EXEC',# dummy
                'submitter': 'SET_ON_EXEC',# dummy
                'log_path': os.path.abspath(os.path.join(args.outdir, MASTERLOG))}

    logger.info("Writing config and rc files")
    write_cluster_config(args.outdir, BASEDIR)
    pipeline_cfgfile = write_merged_usr_and_default_cfg(
        BASEDIR, args.outdir, user_data, elm_data)
    write_snakemake_env(os.path.join(args.outdir, RC_FILES['SNAKEMAKE_ENV']), pipeline_cfgfile)
    write_dk_init(os.path.join(args.outdir, RC_FILES['DK_INIT']))
    write_snakemake_init(os.path.join(args.outdir, RC_FILES['SNAKEMAKE_INIT']))

    logger.info("Writing the run file for site %s", site)
    snakefile_abs = os.path.abspath(os.path.join(BASEDIR, "Snakefile"))
    write_run_template_and_exec(site, args.outdir, snakefile_abs, PIPELINE_NAME,
                                args.master_q, args.slave_q, args.no_run)


if __name__ == "__main__":
    main()
