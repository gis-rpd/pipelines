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
import subprocess
#import string
from collections import namedtuple, OrderedDict

#--- third-party imports
#
import yaml

#--- project specific imports
#
from pipelines import get_pipeline_version, get_site, get_rpd_vars
from pipelines import write_dk_init, write_snakemake_init, write_snakemake_env
from pipelines import write_cluster_config, generate_timestamp


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# based on ReadUnit (SG10K)
SampleUnit = namedtuple('SampleUnit', ['run_id', 'flowcell_id', 'library_id',
                                       'lane_id', 'rg_id', 'sample_dir'])

BASEDIR = os.path.dirname(sys.argv[0])

# same as folder name. also used for cluster job names
PIPELINE_NAME = "bcl2fastq"

SAMPLE_CONFIG = "sample_info.yaml"

# log dir relative to outdir
LOG_DIR_REL = "logs"
# master log relative to outdir
MASTERLOG = os.path.join(LOG_DIR_REL, "snakemake.log")
SUBMISSIONLOG = os.path.join(LOG_DIR_REL, "submission.log")

# RC files
RC = {
    'DK_INIT' : 'dk_init.rc',# used to load dotkit
    'SNAKEMAKE_INIT' : 'snakemake_init.rc',# used to load snakemake
    'SNAKEMAKE_ENV' : 'snakemake_env.rc',# used as bash prefix within snakemakejobs
}

# global logger
LOG = logging.getLogger()



def write_pipeline_config(outdir, user_data, elm_data, force_overwrite=False):
    """writes config file for use in snakemake becaused on default config

    FIXME is there a way to retain comments from the template
    """

    rpd_vars = get_rpd_vars()
    for k, v in rpd_vars.items():
        LOG.debug("{} : {}".format(k, v))

    pipeline_config_in = os.path.join(BASEDIR, "conf.default.yaml".format())
    pipeline_config_out = os.path.join(outdir, "conf.yaml".format())

    assert os.path.exists(pipeline_config_in)
    if not force_overwrite:
        assert not os.path.exists(pipeline_config_out), pipeline_config_out

    with open(pipeline_config_in, 'r') as fh:
        config = yaml.safe_load(fh)
    config.update(user_data)

    config['ELM'] = elm_data

    with open(pipeline_config_out, 'w') as fh:
        # default_flow_style=None(default)|True(least readable)|False(most readable)
        yaml.dump(config, fh, default_flow_style=False)

    return pipeline_config_out


def get_sample_unit_from_cfgfile(cfgfile):
    """FIXME:add-doc"""
    sample_units = []
    with open(cfgfile) as fh_cfg:
        for entry in yaml.safe_load(fh_cfg):
            assert len(entry) == 5
            [run_id, flowcell_id, library_id, lane_id, sample_dir] = entry
            su = SampleUnit._make([run_id, flowcell_id, library_id, lane_id, sample_dir])
            sample_units.append(su)
    return sample_units



def get_machine_run_flowcell_id(runid_and_flowcellid):
    """FIXME
    """

    runid, flowcellid = runid_and_flowcellid.split("_")
    machineid = runid.split("-")[0]
    return machineid, runid, flowcellid


def run_folder_for_run_id(runid_and_flowcellid, site=None):
    """runid has to contain flowcell id

    AKA $RAWSEQDIR

    run_folder_for_run_id('HS004-PE-R00139_BC6A7HANXX')
    >>> "/mnt/seq/userrig/HS004/HS004-PE-R00139_BC6A7HANXX"
    """

    machineid, runid, flowcellid = get_machine_run_flowcell_id(
        runid_and_flowcellid)

    if not site:
        site = get_site()

    if site == "gis":
        rundir = "/mnt/seq/userrig/{}/{}_{}".format(machineid, runid, flowcellid)
    else:
        raise ValueError(site)
    return rundir


def get_bcl2fastq_outdir(runid_and_flowcellid, site=None):
    """
    """
    machineid, runid, flowcellid = get_machine_run_flowcell_id(
        runid_and_flowcellid)

    if not site:
        site = get_site()

    if site == "gis":
        outdir = "/mnt/projects/userrig/{}/{}_{}/bcl2fastq_{}".format(
            machineid, runid, flowcellid, generate_timestamp())
    else:
        raise ValueError(site)
    return outdir


def main():
    """main function
    """

    parser = argparse.ArgumentParser(description=__doc__.format(
        PIPELINE_NAME=PIPELINE_NAME, PIPELINE_VERSION=get_pipeline_version()))
    parser.add_argument('-r', "--runid",
                        help="Run ID plus flowcell ID (clashes with -d)")
    parser.add_argument('-d', "--rundir",
                        help="BCL input directory (clashes with -r)")
    parser.add_argument('-o', "--outdir",
                        help="Output directory (may not exist; required if called by user)")
    parser.add_argument('-w', '--slave-q',
                        help="Queue to use for slave jobs")
    parser.add_argument('-m', '--master-q',
                        help="Queue to use for master job")
    parser.add_argument('-l', '--lane', type=int,
                        help="Limit run to this lane")
    parser.add_argument('-i', '--mismatches', type=int,
                        help="Max. number of allowed barcode mismatches (0>=x<=2)"
                        " (default as specified by Illumina)")
    parser.add_argument('-n', '--no-run', action='store_true')
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-q', '--quiet', action='count', default=0)

    args = parser.parse_args()

    # Repeateable -v and -q for setting logging level.
    # See https://gist.github.com/andreas-wilm/b6031a84a33e652680d4
    logging_level = logging.WARN + 10*args.quiet - 10*args.verbose
    logging.basicConfig(level=logging_level,
                        format='%(levelname)s [%(asctime)s]: %(message)s')

    if args.mismatches > 2 or args.mismatches < 0:
        LOG.fatal("Number of mismatches must be between 0-2")
        sys.exit(1)

    if args.lane > 8 or args.lane < 1:
        LOG.fatal("Lane number must be between 1-8")
        sys.exit(1)

    if args.runid and args.rundir:
        LOG.fatal("Cannot use run-id and input directory arguments simultaneously")
        sys.exit(1)
    elif args.runid:
        rundir = run_folder_for_run_id(args.runid)
    elif args.rundir:
        rundir = args.rundir
    else:
        LOG.fatal("Need either run-id or input directory")
        sys.exit(1)
    assert os.path.exists(rundir)

    if not args.outdir:
        outdir = get_bcl2fastq_outdir(args.runid)
    else:
        outdir = args.outdir
    assert not os.path.exists(outdir)
    LOG.info("Writing to {}".format(outdir))


    LOG.critical("Call generate_config.py and pass down {} as {}".format(
        outdir, SAMPLE_CONFIG))
    sample_units = get_sample_unit_from_cfgfile(SAMPLE_CONFIG)


    LOG.info("Writing config and rc files")
    write_cluster_config(args.outdir, BASEDIR)


    LOG.critical("Handle mismatches and lanes")


    # turn arguments into user_data that gets merged into pipeline config
    user_data = {}
    user_data['units'] = OrderedDict()
    for su in sample_units:
        k = su.sample_dir# unique already
        user_data['units'][k] = su._asdict()


    if args.runid:
        log_library_id = [su.library_id for su in sample_units]
        log_lane_id = [su.lane_id for su in sample_units]
        _, log_run_id, _ = get_machine_run_flowcell_id(args.runid)
        log_run_id = len(log_lane_id) * [log_run_id]
    else:
        raise NotImplementedError
    elm_data = {'run_id': log_run_id,
                'library_id': log_library_id,
                'lane_id': log_lane_id,
                'pipeline_name': PIPELINE_NAME,
                'pipeline_version': get_pipeline_version(),
                'site': get_site(),
                'instance_id': 'SET_ON_EXEC',# dummy
                'submitter': 'SET_ON_EXEC',# dummy
                'log_path': os.path.abspath(os.path.join(args.outdir, MASTERLOG))}

    pipeline_cfgfile = write_pipeline_config(args.outdir, user_data, elm_data)
    write_dk_init(os.path.join(args.outdir, RC['DK_INIT']))
    write_snakemake_init(os.path.join(args.outdir, RC['SNAKEMAKE_INIT']))
    write_snakemake_env(os.path.join(args.outdir, RC['SNAKEMAKE_ENV']), pipeline_cfgfile)

    site = get_site()
    if site == "gis":
        LOG.info("Writing the run file for site {}".format(site))
        run_template = os.path.join(BASEDIR, "run.template.sh")
        run_out = os.path.join(args.outdir, "run.sh")
        # if we copied the snakefile (to allow for local modification)
        # the rules import won't work.  so use the original file
        snakefile = os.path.abspath(os.path.join(BASEDIR, "Snakefile"))
        assert not os.path.exists(run_out)
        with open(run_template) as templ_fh, open(run_out, 'w') as out_fh:
            for line in templ_fh:
                line = line.replace("@SNAKEFILE@", snakefile)
                line = line.replace("@LOGDIR@", LOG_DIR_REL)
                line = line.replace("@MASTERLOG@", MASTERLOG)
                line = line.replace("@PIPELINE_NAME@", PIPELINE_NAME)
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
            os.path.dirname(run_out), master_q_arg, run_out, SUBMISSIONLOG)
        if args.no_run:
            LOG.warn("Skipping pipeline run on request. Once ready, use: {}".format(cmd))
            LOG.warn("Once ready submit with: {}".format(cmd))
        else:
            LOG.info("Starting pipeline: {}".format(cmd))
            os.chdir(os.path.dirname(run_out))
            _ = subprocess.check_output(cmd, shell=True)
            submission_log_abs = os.path.abspath(os.path.join(args.outdir, SUBMISSIONLOG))
            master_log_abs = os.path.abspath(os.path.join(args.outdir, MASTERLOG))
            LOG.info("For submission details see {}".format(submission_log_abs))
            LOG.info("The (master) logfile is {}".format(master_log_abs))
    else:
        raise ValueError(site)


if __name__ == "__main__":
    main()
