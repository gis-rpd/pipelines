#!/usr/bin/env python3
"""{PIPELINE_NAME} pipeline (version: {PIPELINE_VERSION}): creates
pipeline-specific config files to given output directory and runs the
pipeline (unless otherwise requested).

If multiple fastq files/pairs are given, a new read-group will be
created per file/pair (changeable in the created conf.yaml).
"""
# {PIPELINE_NAME} and {PIPELINE_VERSION} replaced for printing usage


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


#--- standard library imports
#
import sys
import os
import argparse
import logging
from itertools import zip_longest
import shutil
import json
import subprocess
import string

#--- third-party imports
#
import yaml

#--- project specific imports
#/


# same as folder name
PIPELINE_NAME = "SG10K"

# log dir relative to outdir
LOG_DIR_REL = "logs"
# master log relative to outdir
MASTERLOG = os.path.join(LOG_DIR_REL, "snakemake.{}.log".format(PIPELINE_NAME))

INIT = {
    'gis': "/mnt/projects/rpd/init"
}

# RC files
RC = {
    'DK_INIT' : 'dk_init.rc',# used to load dotkit
    'SNAKEMAKE_INIT' : 'snakemake_init.rc',# used to load snakemake
    'SNAKEMAKE_ENV' : 'snakemake_env.rc',# used as bash prefix within snakemakejobs
}

BASEDIR = os.path.dirname(sys.argv[0])

# global logger
LOG = logging.getLogger()


def get_pipeline_version():
    """determine pipeline version as defined by updir file
    """
    version_file = os.path.abspath(os.path.join(BASEDIR, "..", "VERSION"))
    with open(version_file) as fh:
        version = fh.readline().strip()
    return version


def testing_is_active():
    """checks whether this is a developers version of production
    """
    check_file = os.path.abspath(os.path.join(BASEDIR, "..", "DEVELOPERS_VERSION"))
    #LOG.debug("check_file = {}".format(check_file))
    return os.path.exists(check_file)


def get_site():
    """Determine site where we're running. Throws ValueError if unknown
    """
    # this is a bit naive... but socket.getfqdn() is also useless
    if os.path.exists("/mnt/projects/rpd/") and os.path.exists("/mnt/software"):
        return "gis"
    else:
        raise ValueError("unknown site")


def get_init_call():
    """return dotkit init call
    """
    site = get_site()
    try:
        cmd = [INIT[get_site()]]
    except KeyError:
        raise ValueError("unknown or unconfigured or site {}".format(site))

    if testing_is_active():
        cmd.append('-d')

    return cmd


def get_rpd_vars():
    """Read RPD variables set by calling and parsing output from init
    """

    cmd = get_init_call()
    try:
        res = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        LOG.fatal("Couldn't call init as '{}'".format(' '.join(cmd)))
        raise

    rpd_vars = dict()
    for line in res.decode().splitlines():
        if line.startswith('export '):
            line = line.replace("export ", "")
            line = ''.join([c for c in line if c not in '";\''])
            #LOG.debug("line = {}".format(line))
            k, v = line.split('=')
            rpd_vars[k.strip()] = v.strip()
    return rpd_vars


def write_dk_init(rc_file, overwrite=False):
    """creates dotkit init rc
    """
    if not overwrite:
        assert not os.path.exists(rc_file), rc_file
    with open(rc_file, 'w') as fh:
        fh.write("eval `{}`;\n".format(' '.join(get_init_call())))


def write_snakemake_init(rc_file, overwrite=False):
    """creates file which loads snakemake
    """
    if not overwrite:
        assert not os.path.exists(rc_file), rc_file
    with open(rc_file, 'w') as fh:
        fh.write("# initialize snakemake. requires pre-initialized dotkit\n")
        fh.write("reuse -q miniconda-3\n")
        fh.write("source activate snakemake-3.5.4\n")


def write_snakemake_env(rc_file, config, overwrite=False):
    """creates file for use as bash prefix within snakemake
    """
    if not overwrite:
        assert not os.path.exists(rc_file), rc_file

    with open(rc_file, 'w') as fh_rc:
        fh_rc.write("# used as bash prefix within snakemake\n\n")
        fh_rc.write("# init dotkit\n")
        fh_rc.write("source dk_init.rc\n\n")

        fh_rc.write("# load modules\n")
        with open(config) as fh_cfg:
            for k, v in yaml.safe_load(fh_cfg)["modules"].items():
                fh_rc.write("reuse -q {}\n".format("{}-{}".format(k, v)))

        fh_rc.write("\n")
        fh_rc.write("# unofficial bash strict has to come last\n")
        fh_rc.write("set -euo pipefail;\n")


def write_cluster_config(outdir, force_overwrite=False):
    """writes site dependend cluster config
    """
    cluster_config_in = os.path.join(BASEDIR, "cluster.{}.yaml".format(get_site()))
    cluster_config_out = os.path.join(outdir, "cluster.yaml")

    assert os.path.exists(cluster_config_in)
    if not force_overwrite:
        assert not os.path.exists(cluster_config_out), cluster_config_out

    shutil.copyfile(cluster_config_in, cluster_config_out)


def write_pipeline_config(outdir, user_data, force_overwrite=False):
    """writes config file for use in snakemake becaused on default config

    FIXME is there a way to retain comments from the tempalte
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

    # trick to traverse dictionary fully and replace all instances of variable
    config = dict(json.loads(
        json.dumps(config).replace("$RPD_GENOMES", rpd_vars['RPD_GENOMES'])))

    # for ELM logging
    assert 'ELM' not in config
    config['ELM'] = {'library_id': "FIXME:library_id",
                     'run_id': "FIXME:run_id",
                     'lane_id': "FIXME:lane_id",
                     'pipeline_name': PIPELINE_NAME,
                     'pipeline_version': get_pipeline_version(),
                     'site': get_site()}

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
    parser.add_argument('-1', "--fq1", required=True, nargs="+",
                        help="FastQ file #1 (gzip recommended)."
                        " Multiple (split) input files supported (auto-sorted)")
    parser.add_argument('-2', "--fq2", required=True, nargs="+",
                        help="FastQ file #2 (gzip recommended)."
                        " Multiple (split) input files supported (auto-sorted)")
    parser.add_argument('-s', "--sample", required=True,
                        help="Sample name / identifier")
    parser.add_argument('-o', "--outdir", required=True,
                        help="Output directory (may not exist)")
    parser.add_argument('-n', '--no-run', action='store_true')
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-q', '--quiet', action='count', default=0)

    args = parser.parse_args()


    # Repeateable -v and -q for setting logging level.
    # See https://gist.github.com/andreas-wilm/b6031a84a33e652680d4
    logging_level = logging.WARN + 10*args.quiet - 10*args.verbose
    logging.basicConfig(level=logging_level,
                        format='%(levelname)s [%(asctime)s]: %(message)s')


    # Check fastqs. sorting here should ensure R1 and R2 match
    fq_pairs = list(zip_longest(sorted(args.fq1), sorted(args.fq2)))
    for fq1, fq2 in fq_pairs:
        # only zip_longest uses None if one is missing
        if not fq1 or not fq2:
            LOG.fatal("Mismatching number of fastq files for each end")
            sys.exit(1)
        for f in [fq1, fq2]:
            if not os.path.exists(f):
                LOG.fatal("Non-existing input file {}".format(f))
                sys.exit(1)
    LOG.info("Will process FastQ pairs as follows:\n{}".format("\n".join([
        "#{}: {} and {}".format(i, fq1, fq2) for i, (fq1, fq2) in enumerate(fq_pairs)])))


    if os.path.exists(args.outdir):
        LOG.fatal("Output directory {} already exists".format(args.outdir))
        sys.exit(1)
    # also create log dir immediately
    os.makedirs(os.path.join(args.outdir, LOG_DIR_REL))
    LOG.info("Writing to {}".format(args.outdir))


    # turn arguments into user_data that gets merged into pipeline config
    user_data = {'sample': args.sample}
    user_data['units'] = dict()
    # keys are ascii letters and used for filenaming
    unit_keys = string.ascii_letters
    assert len(fq_pairs) < len(unit_keys)
    for i, (fq1, fq2) in enumerate(fq_pairs):
        user_data['units'][unit_keys[i]] = [fq1, fq2]

    LOG.info("Writing config and rc files")
    write_cluster_config(args.outdir)
    pipeline_cfgfile = write_pipeline_config(args.outdir, user_data)
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
                out_fh.write(line)

                
        submission_log = os.path.join(LOG_DIR_REL, "submission.log")
        submission_log_abs = os.path.abspath(os.path.join(args.outdir, submission_log))
        master_log_abs = os.path.abspath(os.path.join(args.outdir, MASTERLOG))
        
        cmd = "cd {} && qsub {} >> {}".format(os.path.dirname(run_out), run_out, submission_log)
        if args.no_run:
            LOG.warn("Skipping pipeline run on request. Once ready, use: {}".format(cmd))
            LOG.warn("Once ready submit with: {}".format(cmd))
        else:
            LOG.info("Starting pipeline: {}".format(cmd))
            os.chdir(os.path.dirname(run_out))
            res = subprocess.check_output(cmd, shell=True)
            LOG.info("For submission details see {}".format(submission_log_abs))
            LOG.info("The (master) logfile is {}".format(master_log_abs))
    else:
        raise ValueError(site)


if __name__ == "__main__":
    main()
