#!/usr/bin/env python3
"""bcl_stats from Bcl2fastq pipeline
"""

# standard library imports
import logging
import sys
import os
import argparse
import glob
import json

# third party imports
import yaml
import requests

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from config import rest_services
from pipelines import get_machine_run_flowcell_id


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

def main():
    """main function"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--out_dir", required=True, help="out_dir")
    parser.add_argument("-m", "--mux_id", required=True, help="mux_id")
    parser.add_argument('-t', "--test-server", action='store_true',
                        help="Use test-server for stats uploading")
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

    if not os.path.exists(args.out_dir):
        logger.fatal("out_dir %s does not exist", args.out_dir)
        sys.exit(1)
    logger.info("out_dir is %s", args.out_dir)


    confinfo = os.path.join(args.out_dir + '/conf.yaml')
    if not os.path.exists(confinfo):
        logger.fatal("conf info '%s' does not exist under Run directory.\n", confinfo)
        sys.exit(1)
    if args.test_server:
        rest_url = rest_services['stats_upload']['testing']
        logger.info("send status to development server")
    else:
        rest_url = rest_services['stats_upload']['production']
        logger.info("send status to production server")

    with open(confinfo) as fh_cfg:
        yaml_data = yaml.safe_load(fh_cfg)
        assert "run_num" in yaml_data
        runid_with_flowcellid = yaml_data["run_num"]
        _, runid, _ = get_machine_run_flowcell_id(
            runid_with_flowcellid)
        assert "modules" in yaml_data
        soft_ver = yaml_data["modules"].get('bcl2fastq')
        if not soft_ver:
            logger.fatal("bclpath software version %s does not exist", soft_ver)
            sys.exit(1)
        assert "units" in yaml_data
        if not "Project_" + args.mux_id in yaml_data["units"]:
            logger.fatal("mux_id %s does not exist in conf.yaml under %s",
                         args.mux_id, args.out_dir)
            sys.exit(1)

        for k, v in yaml_data["units"].items():
            if k == "Project_{}".format(args.mux_id):
                data = {}
                mux_dir = v.get('mux_dir')
                index_html_path = glob.glob(
                    os.path.join(args.out_dir, "out",
                                 mux_dir, "html/*/all/all/all/lane.html"))
                index_html = index_html_path[0]
                # FIXME should use the snakemake trigger to decide if complete
                if os.path.exists(index_html):
                    logger.info("Uploading stats for completed bcl2fastq %s", mux_dir)
                    data['path'] = index_html
                    data['software'] = soft_ver
                    data['runid'] = runid
                    test_json = json.dumps(data)
                    data_json = test_json.replace("\\", "")
                    headers = {'content-type': 'application/json'}
                    response = requests.post(rest_url, data=data_json, headers=headers)
                    # Response Code is 201 for STATs posting
                    if response.status_code == 201:
                        logger.info("Uploading %s completed successfully", index_html)
                        logger.info("JSON request was %s", data_json)
                        logger.info("Response was %s", response.status_code)
                    else:
                        logger.error("Uploading %s failed", index_html)
                        sys.exit(1)
                else:
                    logger.info("Skipping incomplete (html missing) bcl2fastq in %s", mux_dir)



if __name__ == "__main__":
    logger.info("Stats update starting")
    main()
    logger.info("Successful program exit")
