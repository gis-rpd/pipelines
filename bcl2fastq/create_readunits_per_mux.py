#!/usr/bin/env python3
"""Create readunits perl MUX for bcl2fastq folder
"""
# standard library imports
import os
import sys
import logging
import argparse
import glob
from collections import namedtuple
import yaml

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from readunits import key_for_read_unit

ReadUnit = namedtuple('ReadUnit', ['run_id', 'flowcell_id', 'library_id',
                                   'lane_id', 'rg_id', 'fq1', 'fq2'])

__author__ = "Lavanya Veeravalli"
__email__ = "veeravallil@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)

def check_fastq(fastq_data_dir, laneId):
    """Check if fastq data available for library
    """
    fastq_list = (os.path.join(fastq_data_dir, "*fastq.gz"))
    fastq_data = glob.glob(fastq_list)
    fq1 = fq2 = None
    if len(fastq_data) > 0:
        for file in fastq_data:
            base = os.path.basename(file)
            if "L00laneId_R1_".replace("laneId", laneId) in base:
                fq1 = file
            elif "L00laneId_R2_".replace("laneId", laneId) in base:
                fq2 = file
        if fq2:
            return (True, fq1, fq2)
        else:
            return(True, fq1, None)
    else:
        return (False, None, None)

def main():
    """main function"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-b", "--bcl_out_dir", required=True, help="bcl_out_dir")
    parser.add_argument('-n', "--dry-run", action='store_true',
                        help="Dry run")
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
    # script -qqq -> no loggerging at all
    logger.setLevel(logging.WARN + 10*args.quiet - 10*args.verbose)
    logger.info("bcl_out_dir is %s", args.bcl_out_dir)
    if not os.path.exists(args.bcl_out_dir):
        logger.fatal("out_dir %s does not exist", args.bcl_out_dir)
        sys.exit(1)
    confinfo = os.path.join(args.bcl_out_dir + '/conf.yaml')
    if not os.path.exists(confinfo):
        logger.fatal("conf info '%s' does not exist under Run directory.\n", confinfo)
        sys.exit(1)
    with open(confinfo) as fh_cfg:
        yaml_data = yaml.safe_load(fh_cfg)
        assert "run_num" in yaml_data
        run_num = yaml_data["run_num"]
        assert "units" in yaml_data
        mux_info = {}
        for mux, units in yaml_data["units"].items():
            mux_id = mux.split("_")[-1]
            mux_folder = os.path.join(args.bcl_out_dir, "out", mux)
            if os.path.exists(mux_folder):
                for child in os.listdir(os.path.join(args.bcl_out_dir, "out", mux)):
                    sample_info = {}
                    if child.startswith('Sample'):
                        sample = child.split('_')[-1]
                        sample_path = os.path.join(args.bcl_out_dir, "out", mux, child)
                        sample_dict = {}
                        readunits_dict = {}
                        for lane_id in units["lane_ids"]:
                            status, fq1, fq2 = check_fastq(sample_path, lane_id)
                            if status:
                                ru = ReadUnit(run_num, units["flowcell_id"], sample,\
                                    lane_id, None, fq1, fq2)
                                k = key_for_read_unit(ru)
                                readunits_dict[k] = dict(ru._asdict())
                                sample_dict[sample] = k
                                sample_info = readunits_dict
                                if mux_info.get(mux_id, {}):
                                    mux_info[mux_id].update(sample_info)
                                else:
                                    mux_info[mux_id] = sample_info
    for mux, mux_data in mux_info.items():
        yaml_data = {}
        MUXINFO_CFG = os.path.join(args.bcl_out_dir, mux +".yaml")
        samples_dict = {}
        for key, info in mux_data.items():
            lib = info.get('library_id')
            samples_dict.setdefault(lib, []).append(key)
        yaml_data['samples'] = samples_dict
        yaml_data['readunits'] = mux_data
        if args.dry_run:
            logger.warning("Skipping readunits yaml for %s", mux)
            continue
        with open(MUXINFO_CFG, 'w') as fh:
            fh.write(yaml.dump(yaml_data, default_flow_style=False, explicit_start=True))
            logger.info("readunits yaml for %s under %s", mux, args.bcl_out_dir)
if __name__ == "__main__":
    logger.info("Create sample readunits")
    main()
    logger.info("Successful program exit")
