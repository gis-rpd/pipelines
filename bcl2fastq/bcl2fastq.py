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
import subprocess

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
from pipelines import get_pipeline_version
from pipelines import get_site
from pipelines import get_default_queue
from pipelines import PipelineHandler
from pipelines import get_machine_run_flowcell_id
from pipelines import is_devel_version
from pipelines import logger as aux_logger
from pipelines import generate_timestamp
from pipelines import get_cluster_cfgfile
from config import site_cfg
from generate_bcl2fastq_cfg import MUXINFO_CFG, SAMPLESHEET_CSV, USEBASES_CFG, MuxUnit


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# only dump() and following do not automatically create aliases
yaml.Dumper.ignore_aliases = lambda *args: True


PIPELINE_BASEDIR = os.path.dirname(sys.argv[0])
CFG_DIR = os.path.join(PIPELINE_BASEDIR, "cfg")

# same as folder name. also used for cluster job names
PIPELINE_NAME = "bcl2fastq"


# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)


def get_mux_units_from_cfgfile(cfgfile, restrict_to_lanes=None):
    """if restrict_to_lanes is not None, restrict to these lanes only

    note: mux_units are a list. if there is a case with a mux split
    across multiple lanes the info will be preserved, but might get
    swallowed late if the mux dir should be used as key
    """

    mux_units = []
    with open(cfgfile) as fh_cfg:
        for entry in yaml.safe_load(fh_cfg):
            mu = MuxUnit(**entry)

            if restrict_to_lanes:
                passed_lanes = []
                for lane in mu.lane_ids:
                    if int(lane) in restrict_to_lanes:
                        passed_lanes.append(lane)
                if not passed_lanes:
                    continue# doesn't contain lanes or interest
                elif passed_lanes != mu.lane_ids:
                    mu = mu._replace(lane_ids=passed_lanes)# trim
            mux_units.append(mu)
    return mux_units


def run_folder_for_run_id(runid_and_flowcellid):
    """runid has to contain flowcell id

    AKA $RAWSEQDIR

    run_folder_for_run_id('HS004-PE-R00139_BC6A7HANXX')
    >>> "/mnt/seq/userrig/HS004/HS004-PE-R00139_BC6A7HANXX"
    if machineid eq MS00
    """

    basedir = site_cfg['bcl2fastq_seqdir_base']

    machineid, runid, flowcellid = get_machine_run_flowcell_id(
        runid_and_flowcellid)

    if machineid.startswith('MS00'):# FIXME needs proper cfg handling
        # FIXME untested and unclear for NSCC
        rundir = "{}/{}/MiSeqOutput/{}_{}".format(basedir, machineid, runid, flowcellid)
    else:
        if machineid.startswith('NG0'):# FIXME needs proper cfg handling
            basedir = basedir.replace("userrig", "novogene")    
        rundir = "{}/{}/{}_{}".format(basedir, machineid, runid, flowcellid)

    return rundir


def get_bcl2fastq_outdir(runid_and_flowcellid):
    """where to write bcl2fastq output to
    """

    if is_devel_version():
        basedir = site_cfg['bcl2fastq_outdir_base']['devel']
    else:
        basedir = site_cfg['bcl2fastq_outdir_base']['production']

    machineid, runid, flowcellid = get_machine_run_flowcell_id(
        runid_and_flowcellid)

    outdir = "{basedir}/{mid}/{rid}_{fid}/bcl2fastq_{ts}".format(
        basedir=basedir, mid=machineid, rid=runid, fid=flowcellid,
        ts=generate_timestamp())
    return outdir



def seqrunfailed(mongo_status_script, run_num, outdir, testing):
    """FIXME:add-doc
    """
    logger.info("Setting analysis for %s to %s", run_num, "SEQRUNFAILED")
    analysis_id = generate_timestamp()
    mongo_update_cmd = [mongo_status_script, "-r", run_num, "-s", "SEQRUNFAILED"]
    mongo_update_cmd.extend(["-a", analysis_id, "-o", outdir])
    if testing:
        mongo_update_cmd.append("-t")
    try:
        _ = subprocess.check_output(mongo_update_cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        logger.fatal("The following command failed with return code %s: %s",
                     e.returncode, ' '.join(mongo_update_cmd))
        logger.fatal("Output: %s", e.output.decode())
        logger.fatal("Exiting")
        sys.exit(1)

    flagfile = os.path.join(outdir, "SEQRUNFAILED")
    logger.info("Creating flag file %s", flagfile)
    with open(flagfile, 'w') as _:
        pass


def main():
    """main function
    """

    # FIXME ugly and code duplication in bcl2fastq_dbupdate.py
    mongo_status_script = os.path.abspath(os.path.join(
        os.path.dirname(sys.argv[0]), "mongo_status.py"))
    assert os.path.exists(mongo_status_script)

    parser = argparse.ArgumentParser(description=__doc__.format(
        PIPELINE_NAME=PIPELINE_NAME, PIPELINE_VERSION=get_pipeline_version()))
    parser.add_argument('-r', "--runid",
                        help="Run ID plus flowcell ID (clashes with -d)")
    parser.add_argument('-d', "--rundir",
                        help="BCL input directory (clashes with -r)")
    parser.add_argument('-o', "--outdir",
                        help="Output directory (must not exist; required if called by user)")
    parser.add_argument('-t', "--testing", action='store_true',
                        help="Use MongoDB test server")
    parser.add_argument('--no-archive', action='store_true',
                        help="Don't archieve this analysis")
    parser.add_argument('--name',
                        help="Give this analysis run a name (used in email and report)")
    parser.add_argument('--no-mail', action='store_true',
                        help="Don't send mail on completion")
    default = get_default_queue('slave')
    parser.add_argument('-w', '--slave-q', default=default,
                        help="Queue to use for slave jobs (default: {})".format(default))
    default = get_default_queue('master')
    parser.add_argument('-m', '--master-q', default=default,
                        help="Queue to use for master job (default: {})".format(default))
    parser.add_argument('-l', '--lanes', type=int, nargs="*",
                        help="Limit run to given lane/s (multiples separated by space")
    parser.add_argument('-i', '--mismatches', type=int,
                        help="Max. number of allowed barcode mismatches (0>=x<=2)"
                        " setting a value here overrides the default settings read from ELM)")
    parser.add_argument('-n', '--no-run', action='store_true')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Increase verbosity")
    parser.add_argument('-q', '--quiet', action='count', default=0,
                        help="Decrease verbosity")
    cfg_group = parser.add_argument_group('Configuration files (advanced)')
    for name, descr in [("modules", "modules")]:
        default = os.path.abspath(os.path.join(CFG_DIR, "{}.yaml".format(name)))
        cfg_group.add_argument('--{}-cfg'.format(name),
                               default=default,
                               help="Config-file (yaml) for {}. (default: {})".format(descr, default))


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

    if args.mismatches is not None:
        if args.mismatches > 2 or args.mismatches < 0:
            logger.fatal("Number of mismatches must be between 0-2")
            sys.exit(1)

    lane_info = ''
    lane_nos = []
    if args.lanes:
        lane_info = '--tiles '
        for lane in args.lanes:
            if lane > 8 or lane < 1:
                logger.fatal("Lane number must be between 1-8")
                sys.exit(1)
            else:
                lane_info += 's_{}'.format(lane)+','
        lane_info = lane_info.rstrip()
        lane_info = lane_info[:-1]
        lane_nos = list(args.lanes)


    if args.runid and args.rundir:
        logger.fatal("Cannot use run-id and input directory arguments simultaneously")
        sys.exit(1)
    elif args.runid:
        rundir = run_folder_for_run_id(args.runid)
    elif args.rundir:
        rundir = os.path.abspath(args.rundir)
    else:
        logger.fatal("Need either run-id or input directory")
        sys.exit(1)
    if not os.path.exists(rundir):
        logger.fatal("Expected run directory %s does not exist", rundir)
    logger.info("Rundir is %s", rundir)

    if not args.outdir:
        outdir = get_bcl2fastq_outdir(args.runid)
    else:
        outdir = args.outdir
    if os.path.exists(outdir):
        logger.fatal("Output directory %s already exists", outdir)
        sys.exit(1)
    # create now so that generate_bcl2fastq_cfg.py can run
    os.makedirs(outdir)



    # catch cases where rundir was user provided and looks weird
    try:
        _, runid, flowcellid = get_machine_run_flowcell_id(rundir)
        run_num = runid + "_" + flowcellid
    except:
        run_num = "UNKNOWN-" + rundir.split("/")[-1]


    # call generate_bcl2fastq_cfg
    #
    # FIXME ugly assumes same directory (just like import above). better to import and run main()?
    generate_bcl2fastq = os.path.join(
        os.path.dirname(sys.argv[0]), "generate_bcl2fastq_cfg.py")
    assert os.path.exists(generate_bcl2fastq)
    cmd = [generate_bcl2fastq, '-r', rundir, '-o', outdir]
    if args.testing:
        cmd.append("-t")
    logger.debug("Executing %s", ' ' .join(cmd))
    try:
        res = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        logger.fatal("The following command failed with return code %s: %s",
                     e.returncode, ' '.join(cmd))
        logger.fatal("Output: %s", e.output.decode())
        logger.fatal("Exiting")
        sys.exit(1)
    # generate_bcl2fastq is normally quiet. if there's output, make caller aware of it
    # use sys instead of logger to avoid double logging
    if res:
        sys.stderr.write(res.decode())

    # just created files
    muxinfo_cfg = os.path.join(outdir, MUXINFO_CFG)
    samplesheet_csv = os.path.join(outdir, SAMPLESHEET_CSV)
    usebases_cfg = os.path.join(outdir, USEBASES_CFG)

    # NOTE: signal for failed runs is exit 0 from generate_bcl2fastq and missing output files
    #
    if any([not os.path.exists(x) for x in [muxinfo_cfg, samplesheet_csv, usebases_cfg]]):
        # one missing means all should be missing
        assert all([not os.path.exists(x) for x in [muxinfo_cfg, samplesheet_csv, usebases_cfg]])
        seqrunfailed(mongo_status_script, run_num, outdir, args.testing)
        sys.exit(0)


    # turn arguments into user_data that gets merged into pipeline config
    user_data = {'rundir': rundir,
                 'lanes_arg': lane_info,
                 'samplesheet_csv': samplesheet_csv,
                 'no_archive': args.no_archive,
                 'mail_on_completion': not args.no_mail,
                 'run_num': run_num}
    if args.name:
        user_data['analysis_name'] = args.name


    usebases_arg = ''
    with open(usebases_cfg, 'r') as stream:
        try:
            d = yaml.load(stream)
            assert 'usebases' in d
            assert len(d) == 1# make sure usebases is only key
            for ub in d['usebases']:
                #print (ub)
                usebases_arg += '--use-bases-mask {} '.format(ub)
            #user_data = {'usebases_arg' : usebases_arg}
        except yaml.YAMLError as exc:
            logger.fatal(exc)
            raise
    user_data['usebases_arg'] = usebases_arg
    os.unlink(usebases_cfg)


    mux_units = get_mux_units_from_cfgfile(muxinfo_cfg, lane_nos)
    if args.mismatches is not None:
        mux_units = [mu._replace(barcode_mismatches=args.mismatches)
                     for mu in mux_units]
    os.unlink(muxinfo_cfg)


    user_data['units'] = dict()
    for mu in mux_units:
        # special case: mux split across multiple lanes. make lanes a list
        # and add in extra lanes if needed.
        k = mu.mux_dir
        mu_dict = dict(mu._asdict())
        user_data['units'][k] = mu_dict

    # create mongodb update command, used later, after submission
    mongo_update_cmd = "{} -r {} -s STARTED".format(mongo_status_script, user_data['run_num'])
    mongo_update_cmd += " -a $ANALYSIS_ID -o {}".format(outdir)# set in run.sh
    if args.testing:
        mongo_update_cmd += " -t"

    pipeline_handler = PipelineHandler(
        PIPELINE_NAME, PIPELINE_BASEDIR,
        outdir, user_data,
        logger_cmd=mongo_update_cmd,
        master_q=args.master_q,
        slave_q=args.slave_q,
        modules_cfgfile=args.modules_cfg,
        cluster_cfgfile=get_cluster_cfgfile(CFG_DIR))

    pipeline_handler.setup_env()
    pipeline_handler.submit(args.no_run)





if __name__ == "__main__":
    main()
