#!/usr/bin/env python3
"""Upload SRA request from Bcl2fastq pipeline
"""
# standard library imports
import os
import sys
import logging
import argparse
import json
import glob
import requests
import yaml

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from rest import rest_services

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
    parser.add_argument("-o", "--out_dir", required=True, help="out_dir")
    parser.add_argument("-m", "--mux_id", required=True, help="mux_id")
    parser.add_argument('-t', "--test_server", action='store_true', help="Use STATS uploading to"\
        "test-server here and when calling bcl2fastq wrapper (-t)")
    args = parser.parse_args()
    if not os.path.exists(args.out_dir):
        LOG.fatal("out_dir %s does not exist", args.out_dir)
        sys.exit(1)
    LOG.info("out_dir is %s", args.out_dir)
    confinfo = os.path.join(args.out_dir + '/conf.yaml')
    if not os.path.exists(confinfo):
        LOG.fatal("conf info '%s' does not exist under Run directory.\n", confinfo)
        sys.exit(1)
    if args.test_server:
        rest_url = rest_services['sra_upload']['testing']
        LOG.info("send status to development server")
    else:
        rest_url = rest_services['sra_upload']['production']
        LOG.info("send status to production server")
    email = "rpd@gis.a-star.edu.sg"
    with open(confinfo) as fh_cfg:
        yaml_data = yaml.safe_load(fh_cfg)
        assert "run_num" in yaml_data
        run_num = yaml_data["run_num"]
        assert "units" in yaml_data
        if not "Project_"+args.mux_id in yaml_data["units"]:
            LOG.fatal("mux_id %s does not exist in conf.yaml under %s", \
                args.mux_id, args.out_dir)
            sys.exit(1)
        for k, v in yaml_data["units"].items():
            if k == "Project_{}".format(args.mux_id):
                data = {}
                req = {}
                req_code = {}
                mux_dir = v.get('mux_dir')
                mux_id = v.get('mux_id')
                bcl_success = os.path.join(args.out_dir, "out", mux_dir, "bcl2fastq.SUCCESS")
                if os.path.exists(bcl_success):
                    LOG.info("Bcl2fastq completed for %s hence Upload the STATs", mux_dir)
                    for child in os.listdir(os.path.join(args.out_dir, "out", mux_dir)):
                        if child.startswith('Sample'):
                            sample_path = os.path.join(args.out_dir, "out", mux_dir, child)
                            fastq_data = glob.glob(os.path.join(sample_path, "*fastq.gz"))
                            # if FASTQ data exists
                            if len(fastq_data) > 0:
                                libraryId = child.split('_')[-1]
                                data['libraryId'] = libraryId
                                data['muxId'] = mux_id
                                data['runId'] = run_num
                                data['path'] = [sample_path]
                                data['email'] = [email]
                                req_code['reqCode'] = "SA-A002-009"
                                req_code['SA-A002-009'] = data
                                req['Request'] = req_code
                                test_json = json.dumps(req)
                                data_json = test_json.replace("\\", "")
                                headers = {'content-type': 'application/json'}
                                response = requests.post(rest_url, data=data_json, headers=headers)
                                print(response.status_code)
                                if response.status_code == requests.codes.ok:
                                    LOG.info("Uploading %s completed successfully", \
                                        sample_path)
                                    LOG.info("JSON request was %s", data_json)
                                    LOG.info("Response was %s", response.status_code)
                                else:
                                    LOG.error("Uploading %s completed failed", sample_path)
                                    sys.exit(1)
                            else:
                                LOG.error("There are no fastq file genereated for %s", \
                                    child)
                else:
                    LOG.info("Bcl2fastq is not completed for %s", mux_dir)
                    sys.exit(1)

if __name__ == "__main__":
    LOG.info("STATS update starting")
    main()
    LOG.info("Successful program exit")
