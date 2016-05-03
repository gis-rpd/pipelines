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
import json
import subprocess
#import string
from collections import namedtuple, OrderedDict

#--- third-party imports
#
import yaml

#--- project specific imports
#
from pipelines import get_pipeline_version, get_site, get_rpd_vars
from pipelines import write_dk_init, write_snakemake_init, write_snakemake_env, write_cluster_config
from pipelines import get_reads_unit_from_cfgfile, get_reads_unit_from_args, key_for_read_unit
from pipelines import email_for_user


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


ReadUnit = namedtuple('ReadUnit', ['run_id', 'flowcell_id', 'library_id',
                                   'lane_id', 'rg_id', 'fq1', 'fq2'])

BASEDIR = os.path.dirname(sys.argv[0])

# same as folder name. also used for cluster job names
PIPELINE_NAME = "SG10K"

# log dir relative to outdir
LOG_DIR_REL = "logs"
MASTERLOG = "snakemake.log"
SUBMISSIONLOG = "submission.log"

# RC files
RC = {
    'DK_INIT' : 'dk_init.rc',# used to load dotkit
    'SNAKEMAKE_INIT' : 'snakemake_init.rc',# used to load snakemake
    'SNAKEMAKE_ENV' : 'snakemake_env.rc',# used as bash prefix within snakemakejobs
}


# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)


def write_pipeline_config(outdir, user_data, elm_data, force_overwrite=False):
    """writes config file for use in snakemake becaused on default config

    FIXME is there a way to retain comments from the template
    """

    rpd_vars = get_rpd_vars()
    for k, v in rpd_vars.items():
        logger.debug("{} : {}".format(k, v))

    pipeline_config_in = os.path.join(BASEDIR, "conf.default.yaml".format())
    pipeline_config_out = os.path.join(outdir, "conf.yaml".format())

    assert os.path.exists(pipeline_config_in)
    if not force_overwrite:
        assert not os.path.exists(pipeline_config_out), pipeline_config_out

    with open(pipeline_config_in, 'r') as fh:
        config = yaml.safe_load(fh)
    config.update(user_data)

    # trick to traverse dictionary fully and replace all instances of variable
    config = dict(json.loads(
        json.dumps(config).replace("$RPD_GENOMES", rpd_vars['RPD_GENOMES'])))

    assert 'ELM' not in config
    config['ELM'] = elm_data

    # FIXME we could check presence of files here but would need to
    # iterate over config and assume structure

    with open(pipeline_config_out, 'w') as fh:
        # default_flow_style=None(default)|True(least readable)|False(most readable)
        yaml.dump(config, fh, default_flow_style=False)

    return pipeline_config_out


def main():
    """main function
    """

    parser = argparse.ArgumentParser(description=__doc__.format(
        PIPELINE_NAME=PIPELINE_NAME, PIPELINE_VERSION=get_pipeline_version()))
    parser.add_argument('-1', "--fq1", nargs="+",
                        help="FastQ file/s (gzip only)."
                        " Multiple input files supported (auto-sorted)."
                        " Note: each file gets a unique read group id assigned!"
                        " Collides with -c.")
    parser.add_argument('-2', "--fq2", nargs="+",
                        help="FastQ file/s (if paired) (gzip only). See also --fq1")
    parser.add_argument('-s', "--sample", required=True,
                        help="Sample name")
    parser.add_argument('-c', "--config",
                        help="Config file (YAML) listing: run-, flowcell-, sample-id, lane"
                        " as well as fastq1 and fastq2 per line. Collides with -1, -2")
    parser.add_argument('-o', "--outdir", required=True,
                        help="Output directory (may not exist)")
    parser.add_argument('-w', '--slave-q',
                        help="Queue to use for slave jobs")
    parser.add_argument('-m', '--master-q',
                        help="Queue to use for master job")
    parser.add_argument('-n', '--no-run', action='store_true')
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
    # script -qqq -> no logging at all
    logger.setLevel(logging.WARN + 10*args.quiet - 10*args.verbose)

    if args.config:
        if any([args.fq1, args.fq2]):
            logger.fatal("Config file overrides fastq input arguments. Use one or the other")
            sys.exit(1)
        if not os.path.exists(args.config):
            logger.fatal("Config file {} does not exist".format(args.config))
            sys.exit(1)
        read_units = get_reads_unit_from_cfgfile(args.config)
    else:
        read_units = get_reads_unit_from_args(args.fq1, args.fq2)

    for ru in read_units:
        logger.debug("Checking read unit: {}".format(ru))
        for f in [ru.fq1, ru.fq2]:
            if not os.path.exists(f):
                logger.fatal("Non-existing input file {}".format(f))
                sys.exit(1)

    if os.path.exists(args.outdir):
        logger.fatal("Output directory {} already exists".format(args.outdir))
        sys.exit(1)
    # also create log dir immediately
    os.makedirs(os.path.join(args.outdir, LOG_DIR_REL))
    logger.info("Writing to {}".format(args.outdir))

    # master log has to be abs to work with PBS where we can't cwd with directives
    masterlog = os.path.abspath(os.path.join(args.outdir, LOG_DIR_REL, MASTERLOG))
    submissionlog = os.path.abspath(os.path.join(args.outdir, LOG_DIR_REL, SUBMISSIONLOG))

    logger.info("Writing config and rc files")

    write_cluster_config(args.outdir, BASEDIR)

    # turn arguments into user_data that gets merged into pipeline config
    user_data = {'sample': args.sample}# needed for file naming
    user_data['units'] = OrderedDict()
    for ru in read_units:
        k = key_for_read_unit(ru)
        user_data['units'][k] = ru._asdict()

    elm_data = {'pipeline_name': PIPELINE_NAME,
                'pipeline_version': get_pipeline_version(),
                'site': get_site(),
                'instance_id': 'SET_ON_EXEC',# dummy
                'submitter': 'SET_ON_EXEC',# dummy
                'log_path': masterlog}

    pipeline_cfgfile = write_pipeline_config(args.outdir, user_data, elm_data)
    write_dk_init(os.path.join(args.outdir, RC['DK_INIT']))
    write_snakemake_init(os.path.join(args.outdir, RC['SNAKEMAKE_INIT']))
    write_snakemake_env(os.path.join(args.outdir, RC['SNAKEMAKE_ENV']), pipeline_cfgfile)

    site = get_site()
    if site == "gis" or site=="nscc":
        logger.info("Writing the run file for site {}".format(site))
        run_template = os.path.join(BASEDIR, "..", "lib", "run.template.{}.sh".format(site))
        run_out = os.path.join(args.outdir, "run.sh")
        # if we copied the snakefile (to allow for local modification)
        # the rules import won't work.  so use the original file
        snakefile = os.path.abspath(os.path.join(BASEDIR, "Snakefile"))
        assert not os.path.exists(run_out)
        with open(run_template) as templ_fh, open(run_out, 'w') as out_fh:
            # we don't know for sure who's going to actually exectute
            # but it's very likely the current user, who needs to be notified
            # on qsub kills etc
            toaddr =  email_for_user()
            for line in templ_fh:
                line = line.replace("@SNAKEFILE@", snakefile)
                line = line.replace("@LOGDIR@", LOG_DIR_REL)
                line = line.replace("@MASTERLOG@", masterlog)
                line = line.replace("@PIPELINE_NAME@", PIPELINE_NAME)
                line = line.replace("@MAILTO@", toaddr)
                if args.slave_q:
                    line = line.replace("@DEFAULT_SLAVE_Q@", args.slave_q)
                else:
                    line = line.replace("@DEFAULT_SLAVE_Q@", "")
                out_fh.write(line)

        if args.master_q:
            master_q_arg = "-q {}".format(args.master_q)
        else:
            master_q_arg = ""
        cmd = "cd {} && qsub {} {} >> {}".format(
            os.path.dirname(run_out), master_q_arg, os.path.basename(run_out),
            os.path.relpath(submissionlog, os.path.dirname(run_out)))
        if args.no_run:
            logger.warning("Skipping pipeline run on request. Once ready, use: {}".format(cmd))
            logger.warning("Once ready submit with: {}".format(cmd))
        else:
            logger.info("Starting pipeline: {}".format(cmd))
            os.chdir(os.path.dirname(run_out))
            _ = subprocess.check_output(cmd, shell=True)
            logger.info("For submission details see {}".format(submissionlog))
            logger.info("The (master) logfile is {}".format(masterlog))
    else:
        raise ValueError(site)


if __name__ == "__main__":
    main()
