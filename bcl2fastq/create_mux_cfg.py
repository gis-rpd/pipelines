#!/usr/bin/env python3
"""Create readunits per MUX in bcl2fastq folder
"""

# standard library imports
#
import os
import sys
import logging
import argparse
import glob

# third party imports
#
import yaml

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from readunits import ReadUnit
from readunits import key_for_readunit
from readunits import create_rg_id_from_ru


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
    parser.add_argument("-b", "--bcl2fastq", required=True,
                        help="bcl2fastq directory")
    parser.add_argument("-o", "--outpref",
                        help="Output prefix used for created yaml files per MUX (default: bcl2fastq dir)")
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

    if not os.path.exists(args.bcl2fastq):
        logger.fatal("out_dir %s does not exist", args.bcl2fastq)
        sys.exit(1)

    confinfo = os.path.join(args.bcl2fastq + '/conf.yaml')
    if not os.path.exists(confinfo):
        logger.fatal("conf info '%s' does not exist under Run directory.\n", confinfo)
        sys.exit(1)

    if args.outpref:
        outprefix = args.outpref
    else:
        outprefix = args.bcl2fastq

    # FIXME too many levels of nesting. export to functions
    with open(confinfo) as fh_cfg:
        yaml_data = yaml.safe_load(fh_cfg)
        assert "units" in yaml_data
        assert "run_num" in yaml_data
        run_num = yaml_data["run_num"]

        for mux, units in yaml_data["units"].items():
            mux_id = mux.split("_")[-1]
            mux_folder = os.path.join(args.bcl2fastq, "out", mux)
            if not os.path.exists(mux_folder):
                continue

            # samples and readunits per mux
            samples = {}
            readunits = {}
            for child in os.listdir(os.path.join(args.bcl2fastq, "out", mux)):
                if not child.startswith('Sample'):
                    continue
                sample_id = child.split('_')[-1]
                samples[sample_id] = []
                sample_path = os.path.join(args.bcl2fastq, "out", mux, child)
                for lane_id in units["lane_ids"]:
                    status, fq1, fq2 = check_fastq(sample_path, lane_id)
                    if not status:
                        # FIXME throw error?
                        continue

                    ru = ReadUnit(run_num, units["flowcell_id"], sample_id,
                                  lane_id, None, fq1, fq2)
                    ru = ru._replace(rg_id=create_rg_id_from_ru(ru))
                    k = key_for_readunit(ru)
                    readunits[k] = dict(ru._asdict())
                    samples[sample_id].append(k)

            # write yaml per mux
            muxinfo_cfg = outprefix + mux_id + ".yaml"
            if args.dry_run:
                logger.warning("Skipped creation of %s", muxinfo_cfg)
            else:
                with open(muxinfo_cfg, 'w') as fh:
                    fh.write(yaml.dump(dict(samples=samples), default_flow_style=False))
                    fh.write(yaml.dump(dict(readunits=readunits), default_flow_style=False))
                    logger.info("Created %s", muxinfo_cfg)




if __name__ == "__main__":
    logger.info("Creating sample readunits")
    main()
    logger.info("Successful program exit")
