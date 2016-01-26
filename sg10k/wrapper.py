#!/usr/bin/env python3
"""Pipeline Wrapper for SG10K
"""

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

#--- third-party imports
#
import yaml

#--- project specific imports
#/


# global logger
LOG = logging.getLogger()

INIT = {'gis': "/mnt/projects/rpd/init"}


def testing_is_active():
    """checks whether this is a developers version of production"""
    basedir = os.path.dirname(sys.argv[0])
    check_file = os.path.abspath(os.path.join(basedir, "..", "DEVELOPERS_VERSION"))
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
    """FIXME:add-doc
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


def create_cluster_config(outdir, force_overwrite=False):
    """FIXME:add-doc
    """
    basedir = os.path.dirname(sys.argv[0])
    cluster_config_in = os.path.join(basedir, "cluster.{}.yaml".format(get_site()))
    cluster_config_out = os.path.join(outdir, "cluster.yaml")

    assert os.path.exists(cluster_config_in)
    if not force_overwrite:
        assert not os.path.exists(cluster_config_out)

    shutil.copyfile(cluster_config_in, cluster_config_out)


def create_pipeline_config(outdir, user_data, force_overwrite=False):
    """FIXME:add-doc
    """

    rpd_vars = get_rpd_vars()
    for k, v in rpd_vars.items():
        LOG.debug("{} : {}".format(k, v))
    
    basedir = os.path.dirname(sys.argv[0])
    pipeline_config_in = os.path.join(basedir, "conf.default.yaml".format(get_site()))
    pipeline_config_out = os.path.join(outdir, "conf.yaml".format())

    assert os.path.exists(pipeline_config_in)
    if not force_overwrite:
        assert not os.path.exists(pipeline_config_out)

    with open(pipeline_config_in, 'r') as fh:
        config = yaml.load(fh)
    config.update(user_data)

    # trick to traverse dictionary fully and replace all instances of variable
    config = dict(json.loads(
        json.dumps(config).replace("$RPD_GENOMES", rpd_vars['RPD_GENOMES'])))

    # FIXME we could test presence of files but would need to iterate
    # over config and assume structure
    
    with open(pipeline_config_out, 'w') as fh:
        # default_flow_style=None(default)|True(least readable)|False(most readable)
        yaml.dump(config, fh, default_flow_style=False)


def main():
    """main function
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-1', "--fq1", required=True, nargs="+",
                        help="FastQ file #1 (gzip recommended)."
                        " Multiple (split) input files supported")
    parser.add_argument('-2', "--fq2", required=True, nargs="+",
                        help="FastQ file #2 (gzip recommended)."
                        " Multiple (split) input files supported")
    parser.add_argument('-s', "--sample", required=True,
                        help="Sample name / identifier")
    parser.add_argument('-o', "--outdir", required=True,
                        help="Output directory")
    parser.add_argument('-b', '--no-run', action='store_true')
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('-q', '--quiet', action='count', default=0)
    args = parser.parse_args()

    # Repeateable -v and -q for setting logging level.
    # See https://gist.github.com/andreas-wilm/b6031a84a33e652680d4
    logging_level = logging.WARN + 10*args.quiet - 10*args.verbose
    logging.basicConfig(level=logging_level,
                        format='%(levelname)s [%(asctime)s]: %(message)s')

    # check fastqs. sorting here should ensure R1 and R2 match
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

    if os.path.exists(args.outdir):
        LOG.fatal("Output directory {} already exists".format(args.outdir))
        sys.exit(1)
    os.makedirs(args.outdir)
    LOG.info("Writing to {}".format(args.outdir))
    
    # turn arguments into user_data that gets merged into pipeline config
    user_data = {'sample': args.sample}
    user_data['units'] = dict()
    for i, (fq1, fq2) in enumerate(fq_pairs):
        user_data['units'][chr(ord('A')+i)] = [fq1, fq2]

    LOG.info("Writing config files")
    create_cluster_config(args.outdir)
    create_pipeline_config(args.outdir, user_data)

    site = get_site()
    if site == "gis":
        LOG.info("Writing the run file")
        basedir = os.path.dirname(sys.argv[0])
        run_template = os.path.join(basedir, "run.qsub.template.sh")
        run_out = os.path.join(args.outdir, "run.qsub.sh")
        init_call = get_init_call()
        # can't copy snakefile because we need the relative rules directory
        snakefile = os.path.abspath(os.path.join(basedir, "Snakefile"))
        assert not os.path.exists(run_out)
        with open(run_template) as templ_fh, open(run_out, 'w') as out_fh:
            for line in templ_fh:
                # FIXME not working and replaced through r
                line = line.replace("@INIT@", ' '.join(init_call))
                line = line.replace("@SNAKEFILE@", snakefile)
                out_fh.write(line)
                
        if args.no_run:
            cmd = "cd {} && qsub {}".format(os.path.dirname(run_out), run_out)
            print("Not actually running pipeline. Once ready use:".format(cmd))
        else:
            LOG.warn("Cheating with dk.rc")
            shutil.copy("dk.rc", os.path.dirname(run_out))
            
            os.chdir(os.path.dirname(run_out))
            subprocess.check_call(["qsub", run_out])                  

    else:
        raise ValueError(site)

if __name__ == "__main__":
    main()
