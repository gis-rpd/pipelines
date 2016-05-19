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
from pipelines import get_pipeline_version, get_site, get_rpd_vars
from pipelines import write_dk_init, write_snakemake_init, write_snakemake_env
from pipelines import write_cluster_config, generate_timestamp
from pipelines import get_machine_run_flowcell_id, is_devel_version
from pipelines import email_for_user
from generate_bcl2fastq_cfg import MUXINFO_CFG, SAMPLESHEET_CSV, USEBASES_CFG, MuxUnit


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# only dump() and following do not automatically create aliases
yaml.Dumper.ignore_aliases = lambda *args: True


BASEDIR = os.path.dirname(sys.argv[0])

# same as folder name. also used for cluster job names
PIPELINE_NAME = "bcl2fastq"

# log dir relative to outdir
LOG_DIR_REL = "logs"
# master log relative to outdir
MASTERLOG = os.path.join(LOG_DIR_REL, "snakemake.log")
SUBMISSIONLOG = os.path.join(LOG_DIR_REL, "submission.log")
PIPELINE_CONFIG_FILE = "conf.yaml"
PIPELINE_DEFAULT_CONFIG_FILE = "conf.default.yaml"

# RC files
RC = {
    'DK_INIT' : 'dk_init.rc',# used to load dotkit
    'SNAKEMAKE_INIT' : 'snakemake_init.rc',# used to load snakemake
    'SNAKEMAKE_ENV' : 'snakemake_env.rc',# used as bash prefix within snakemakejobs
}

DEFAULT_SLAVE_Q = {'gis': None,
                   'nscc': 'production'}
DEFAULT_MASTER_Q = {'gis': None,
                    'nscc': 'production'}

# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)


def write_pipeline_config(outdir, user_data, elm_data, force_overwrite=False):
    """writes config file for use in snakemake based on default config,
    user data and elm data to outdir.
    """

    rpd_vars = get_rpd_vars()
    for k, v in rpd_vars.items():
        logger.debug("{} : {}".format(k, v))

    pipeline_config_in = os.path.join(BASEDIR, PIPELINE_DEFAULT_CONFIG_FILE)
    pipeline_config_out = os.path.join(outdir, PIPELINE_CONFIG_FILE)

    assert os.path.exists(pipeline_config_in)
    if not force_overwrite:
        assert not os.path.exists(pipeline_config_out), pipeline_config_out

    with open(pipeline_config_in, 'r') as fh:
        config = yaml.safe_load(fh)
    config.update(user_data)

    config['ELM'] = elm_data

    #import pdb; pdb.set_trace()
    with open(pipeline_config_out, 'w') as fh:
        # default_flow_style=None(default)|True(least readable)|False(most readable)
        yaml.dump(config, fh, default_flow_style=False)

    return pipeline_config_out


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


def run_folder_for_run_id(runid_and_flowcellid, site=None):
    """runid has to contain flowcell id

    AKA $RAWSEQDIR

    run_folder_for_run_id('HS004-PE-R00139_BC6A7HANXX')
    >>> "/mnt/seq/userrig/HS004/HS004-PE-R00139_BC6A7HANXX"
    if machineid eq MS00
    """

    basedir_map = {
        'gis': '/mnt/seq/userrig/',
        'nscc': '/seq/astar/gis/userrig/'
        }

    if not site:
        site = get_site()
    if site not in basedir_map:
        raise ValueError(site)
    basedir = basedir_map[site]

    machineid, runid, flowcellid = get_machine_run_flowcell_id(
        runid_and_flowcellid)

    if machineid.startswith('MS00'):
        # FIXME untested and unclear for NSCC
        rundir = "{}/{}/MiSeqOutput/{}_{}".format(basedir, machineid, runid, flowcellid)
    else:
        rundir = "{}/{}/{}_{}".format(basedir, machineid, runid, flowcellid)

    return rundir


def get_bcl2fastq_outdir(runid_and_flowcellid, site=None):
    """
    """

    basedir_map = {
        'gis': {
            'devel': '/mnt/projects/rpd/testing/output/bcl2fastq',
            'production': '/mnt/projects/userrig/solexa/'},
        'nscc': {
            'devel': '/seq/astar/gis/rpd/testing/output/bcl2fastq/',
            'production': '/seq/astar/gis/userrig/'}
        }

    if not site:
        site = get_site()
    if site not in basedir_map:
        raise ValueError(site)

    if is_devel_version():
        basedir = basedir_map[site]['devel']
    else:
        basedir = basedir_map[site]['production']

    machineid, runid, flowcellid = get_machine_run_flowcell_id(
        runid_and_flowcellid)

    outdir = "{basedir}/{mid}/{rid}_{fid}/bcl2fastq_{ts}".format(
        basedir=basedir, mid=machineid, rid=runid, fid=flowcellid,
        ts=generate_timestamp())
    return outdir



def seqrunfailed(mongo_status_script, run_num, outdir, testing):
    """FIXME:add-doc
    """
    logger.info("Setting analysis for {} to {}".format(run_num, "SEQRUNFAILED"))
    analysis_id = generate_timestamp()
    mongo_update_cmd = [mongo_status_script, "-r", run_num, "-s", "SEQRUNFAILED"]
    mongo_update_cmd.extend(["-a", analysis_id, "-o", outdir])
    if testing:
        mongo_update_cmd.append("-t")
    try:
        _ = subprocess.check_output(mongo_update_cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        logger.fatal("The following command failed with return code {}: {}".format(
            e.returncode, ' '.join(mongo_update_cmd)))
        logger.fatal("Output: {}".format(e.output.decode()))
        logger.fatal("Exiting")
        sys.exit(1)

    flagfile = os.path.join(outdir, "SEQRUNFAILED")
    logger.info("Creating flag file {}".format(flagfile))
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
                        help="Output directory (may not exist; required if called by user)")
    parser.add_argument('-t', "--testing", action='store_true',
                        help="Use MongoDB test server")
    parser.add_argument('--no-mail', action='store_true',
                        help="Don't send mail on completion")
    parser.add_argument('-w', '--slave-q',
                        help="Queue to use for slave jobs (defaults: {})".format(DEFAULT_SLAVE_Q))
    parser.add_argument('-m', '--master-q',
                        help="Queue to use for master job (defaults: {})".format(DEFAULT_MASTER_Q))
    parser.add_argument('-l', '--lanes', type=int, nargs="*",
                        help="Limit run to given lane/s (multiples separated by space")
    parser.add_argument('-i', '--mismatches', type=int,
                        help="Max. number of allowed barcode mismatches (0>=x<=2)"
                        " setting a value here overrides the default settings read from ELM)")
    parser.add_argument('-n', '--no-run', action='store_true')
    parser.add_argument('-v', '--verbose', action='count', default=1,
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
        logger.fatal("Expected run directory {} does not exist".format(rundir))
    logger.info("Rundir is {}".format(rundir))

    if not args.outdir:
        outdir = get_bcl2fastq_outdir(args.runid)
    else:
        outdir = args.outdir
    assert not os.path.exists(outdir)
    logger.info("Writing to {}".format(outdir))
    # create log dir and hence parent dir immediately
    os.makedirs(os.path.join(outdir, LOG_DIR_REL))


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
    logger.debug("Executing {}".format(' ' .join(cmd)))
    try:
        res = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        logger.fatal("The following command failed with return code {}: {}".format(
            e.returncode, ' '.join(cmd)))
        logger.fatal("Output: {}".format(e.output.decode()))
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
                 'mail_on_completion': not args.no_mail,
                 'run_num': run_num}


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


    #user_data['units'] = OrderedDict()
    user_data['units'] = dict()# FIXME does it matter if ordered or not?
    for mu in mux_units:
        # special case: mux split across multiple lanes. make lanes a list and add in extra lanes if needed.
        k = mu.mux_dir
        mu_dict = dict(mu._asdict())
        #print ("TESTING {}".format(mu_dict))
        user_data['units'][k] = mu_dict


    log_library_id = []
    log_lane_id = []
    log_run_id = []
    # one entry per mux and lane
    for mu in mux_units:
        for lane in mu.lane_ids:# can have multiple lanes per mux
            log_library_id.append(mu.mux_id)# logger allows mux_id and lib_id switching
            log_lane_id.append(lane)
            log_run_id.append(mu.run_id)

    elm_data = {'pipeline_name': PIPELINE_NAME,
                'pipeline_version': get_pipeline_version(),
                'site': get_site(),
                'instance_id': 'SET_ON_EXEC',# dummy
                'submitter': 'SET_ON_EXEC',# dummy
                'log_path': os.path.abspath(os.path.join(outdir, MASTERLOG))}

    logger.debug("Writing config and rc files")
    pipeline_cfgfile = write_pipeline_config(outdir, user_data, elm_data)
    write_cluster_config(outdir, BASEDIR)
    write_dk_init(os.path.join(outdir, RC['DK_INIT']))
    write_snakemake_init(os.path.join(outdir, RC['SNAKEMAKE_INIT']))
    write_snakemake_env(os.path.join(outdir, RC['SNAKEMAKE_ENV']), pipeline_cfgfile)


    # create mongodb update command, used later, after queueing
    mongo_update_cmd = "{} -r {} -s STARTED".format(mongo_status_script, user_data['run_num'])
    mongo_update_cmd += " -a $ANALYSIS_ID -o {}".format(outdir)# set in run.sh
    if args.testing:
        mongo_update_cmd += " -t"


    site = get_site()
    if site == "gis" or site == "nscc":
        logger.debug("Writing the run file for site {}".format(site))
        run_template = os.path.join(BASEDIR, "run.template.{}.sh".format(site))
        run_out = os.path.join(outdir, "run.sh")
        # if we copied the snakefile (to allow for local modification)
        # the rules import won't work.  so use the original file
        snakefile = os.path.abspath(os.path.join(BASEDIR, "Snakefile"))
        assert not os.path.exists(run_out)
        with open(run_template) as templ_fh, open(run_out, 'w') as out_fh:
            # we don't know for sure who's going to actually exectute
            # but it's very likely the current user, who needs to be notified
            # on qsub kills etc
            toaddr = email_for_user()
            for line in templ_fh:
                line = line.replace("@SNAKEFILE@", snakefile)
                line = line.replace("@LOGDIR@", LOG_DIR_REL)
                line = line.replace("@MASTERLOG@", MASTERLOG)
                line = line.replace("@PIPELINE_NAME@", PIPELINE_NAME)
                line = line.replace("@MAILTO@", toaddr)
                if args.slave_q:
                    line = line.replace("@DEFAULT_SLAVE_Q@", args.slave_q)
                else:
                    if DEFAULT_SLAVE_Q[site] is not None:
                        line = line.replace("@DEFAULT_SLAVE_Q@", DEFAULT_SLAVE_Q[site])
                    else:
                        line = line.replace("@DEFAULT_SLAVE_Q@", "")

                line = line.replace("@MONGO_UPDATE_CMD@", mongo_update_cmd)
                out_fh.write(line)

        if args.master_q:
            master_q_arg = "-q {}".format(args.master_q)
        else:
            if DEFAULT_MASTER_Q[site] is not None:
                master_q_arg = "-q {}".format(DEFAULT_MASTER_Q[site])
            else:
                master_q_arg = ""

        cmd = "cd {} && qsub {} {} >> {}".format(
            os.path.dirname(run_out), master_q_arg, os.path.basename(run_out), SUBMISSIONLOG)

        if args.no_run:
            logger.warning("Skipping pipeline run on request. Once ready, use: {}".format(cmd))
            logger.warning("Once ready submit with: {}".format(cmd))
        else:
            logger.info("Starting pipeline: {}".format(cmd))
            #os.chdir(os.path.dirname(run_out))
            _ = subprocess.check_output(cmd, shell=True)
            submission_log_abs = os.path.abspath(os.path.join(outdir, SUBMISSIONLOG))
            master_log_abs = os.path.abspath(os.path.join(outdir, MASTERLOG))
            logger.info("For submission details see {}".format(submission_log_abs))
            logger.info("The (master) logfile is {}".format(master_log_abs))
    else:
        raise ValueError(site)


if __name__ == "__main__":
    main()
