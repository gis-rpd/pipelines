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
from pipelines import get_pipeline_version
from pipelines import ref_is_indexed
from pipelines import get_site
from pipelines import PipelineHandler
from pipelines import logger as pipelines_logger
from readunits import logger as readunits_logger
from readunits import get_reads_unit_from_cfgfile, get_reads_unit_from_args, key_for_read_unit


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# only dump() and following do not automatically create aliases
yaml.Dumper.ignore_aliases = lambda *args: True


PIPELINE_BASEDIR = os.path.dirname(sys.argv[0])

# same as folder name. also used for cluster job names
PIPELINE_NAME = "star-rsem"

DEFAULT_SLAVE_Q = {'GIS': None,
                   'NSCC': 'production'}
DEFAULT_MASTER_Q = {'GIS': None,
                    'NSCC': 'production'}

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
    parser.add_argument('-c', "--config",
                        help="Config file (YAML) listing: run-, flowcell-, sample-id, lane"
                        " as well as fastq1 and fastq2 per line. Will create a new RG per line,"
                        " unless read groups is set in last column. Collides with -1, -2")
    parser.add_argument('-o', "--outdir", required=True,
                        help="Output directory (must not exist)")
    parser.add_argument('-C', "--cuffdiff", action='store_true',
                        dest="run_cuffdiff",
                        help="Also run cuffdiff")
    parser.add_argument('-S', '--stranded', action='store_true',
                        help="Stranded library prep (default is unstranded)")
    parser.add_argument('--no-mail', action='store_true',
                        help="Don't send mail on completion")
    site = get_site()
    default = DEFAULT_SLAVE_Q.get(site, None)
    parser.add_argument('-w', '--slave-q', default=default,
                        help="Queue to use for slave jobs (default: {})".format(default))
    default = DEFAULT_MASTER_Q.get(site, None)
    parser.add_argument('-m', '--master-q', default=default,
                        help="Queue to use for master job (default: {})".format(default))
    parser.add_argument('-n', '--no-run', action='store_true')
    parser.add_argument('-v', '--verbose', action='count', default=1)
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
    pipelines_logger.setLevel(logging.WARN + 10*args.quiet - 10*args.verbose)
    readunits_logger.setLevel(logging.WARN + 10*args.quiet - 10*args.verbose)

    # FIXME checks on reffa index (currently not exposed via args)
    
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


    # turn arguments into user_data that gets merged into pipeline config
    user_data = {'mail_on_completion': not args.no_mail,
                 'stranded': args.stranded,
                 'run_cuffdiff': args.run_cuffdiff}
    user_data['readunits'] = dict()
    user_data['paired_end'] = read_units[0].fq2 is not None
    for ru in read_units:
        k = key_for_read_unit(ru)
        user_data['readunits'][k] = dict(ru._asdict())
        # consistency check
        if ru.fq2:
            assert user_data['paired_end']
        else:
            assert not user_data['paired_end']
            
    # samples is a dictionary with sample names as key (here just one)
    # each value is a list of readunits
    user_data['samples'] = dict()
    user_data['samples'][args.sample] = list(user_data['readunits'].keys())

    pipeline_handler = PipelineHandler(
        PIPELINE_NAME, PIPELINE_BASEDIR, args.outdir, user_data,
        site=site, master_q=args.master_q, slave_q=args.slave_q)
    pipeline_handler.setup_env()
    pipeline_handler.submit(args.no_run)


if __name__ == "__main__":
    main()
