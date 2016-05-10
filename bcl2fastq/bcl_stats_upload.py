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
import yaml
import requests

__author__ = "Lavanya Veeravalli"
__email__ = "veeravallil@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# global logger
# http://docs.python.org/library/logging.html
LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] %(levelname)s %(filename)s: %(message)s')


def main():
    """main function"""     
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-bclpath", "--bclpath",
                        dest="bclpath",
                        required=True,
                        help="bclpath, e.g. /mnt/projects/rpd/testing/output/bcl2fastq-commit-2d2df7e-dirty-MS001-PE-R00294_000000000-AH2G7.rdRjIVWoM2/")

    parser.add_argument('-t', "--test_server", action='store_true', help="Use STATS uploading to test-server here and when calling bcl2fastq wrapper (-t)")
    args = parser.parse_args()
    if not os.path.exists(args.bclpath):
        LOG.fatal("bclpath {} does not exist".format(args.bclpath))
    LOG.info("bclpath is {}".format(args.bclpath))
    confinfo = os.path.join(args.bclpath + '/conf.yaml')
    if not os.path.exists(confinfo):
        LOG.fatal("conf info '%s' does not exist under Run directory.\n" % (confinfo))
        sys.exit(1)
    if args.test_server == True:
        rest_url = "http://dlap54v:8058/gisanalysis/rest/resource/submit/new/stats"
        LOG.info("send status to development server")
    elif args.test_server == False:
        LOG.info("FIXME implement the production url")
        LOG.info("send status to production server")
    with open(confinfo) as fh_cfg:
        yaml_data = yaml.safe_load(fh_cfg)
        assert "run_num" in yaml_data
        run_num = yaml_data["run_num"]
        assert "modules" in yaml_data
        soft_ver = yaml_data["modules"].get('bcl2fastq')
        if not soft_ver:
            LOG.fatal("bclpath software version {} does not exist".format(soft_ver))
        assert "units" in yaml_data
        for k, v in yaml_data["units"].items():
            data = {}
            mux_dir = v.get('mux_dir')
            bcl_success = os.path.join(args.bclpath, "out", mux_dir, "bcl2fastq.SUCCESS")
            if os.path.exists(bcl_success):
                LOG.info("Bcl2fastq completed for {} hence Upload the STATs".format(mux_dir))
                index_html_path = glob.glob(os.path.join(args.bclpath, "out", mux_dir, "html/*/all/all/all/lane.html"))
                index_html = index_html_path[0]
                if os.path.exists(index_html):
                    LOG.info("Bcl2fastq completed for {} hence Upload the STATs".format(mux_dir))
                    data['path'] = index_html
                    data['software'] = soft_ver
                    data['runid'] = run_num
                    test_json = json.dumps(data)
                    data_json = test_json.replace("\\", "")
                    headers = {'content-type': 'application/json'}
                    response = requests.post(rest_url, data=data_json, headers=headers)
                    ### Response COde is 201 for STATs posting
                    if response.status_code == 201:
                        LOG.info("Uploading {} completed successfully".format(index_html))
                        LOG.info("JSON request was {}".format(data_json))
                        LOG.info("Response was {}".format(response.status_code))
                    else:
                        LOG.error("Uploading {} failed".format(index_html))
                else:
                    LOG.info("Bcl2fastq not completed for {} hence Skip... Uploading the STATs".format(mux_dir))
            else:
                LOG.info("Bcl2fastq is not completed for {}".format(mux_dir))
            
if __name__ == "__main__":
    LOG.info("STATS update starting")
    main()
    LOG.info("Successful program exit")
