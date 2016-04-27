#!/usr/bin/env python3
"""Upload SRA request from Bcl2fastq pipeline
"""
# standard library imports
import os
import sys
import logging
import argparse
import requests
import json
import yaml

__author__ = "Lavanya Veeravalli"
__email__ = "veeravallil@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# global logger
# http://docs.python.org/library/logging.html
LOG = logging.getLogger("")
logging.basicConfig(level=logging.INFO,
                    format='%(levelname)s [%(asctime)s]: %(message)s')

def usage():
    """print usage info"""
    sys.stderr.write("useage: {} [-1]".format(
        os.path.basename(sys.argv[0])))

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
   
    email = "veeravallil@.gis.a-star.edu.sg"# FIXME

    with open(confinfo) as fh_cfg:
        yaml_data = yaml.safe_load(fh_cfg)
        assert "run_num" in yaml_data
        run_num = yaml_data["run_num"]
        assert "modules" in yaml_data
        assert "units" in yaml_data
        
        for k, v in yaml_data["units"].items():
            data = {}
            req = {}
            req_code = {}
            mux_dir = v.get('mux_dir')
            mux_id = v.get('mux_id')
            bcl_success = os.path.join(args.bclpath, "out", mux_dir, "bcl2fastq.SUCCESS")

            if os.path.exists(bcl_success):
                LOG.info("Bcl2fastq completed for {} hence Upload the STATs".format(mux_dir))
                for child in os.listdir(os.path.join(args.bclpath, "out", mux_dir)):
                    if child.startswith('Sample'):
                        sample_path = os.path.join(args.bclpath, "out", mux_dir, child)
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
                        if args.test_server == True:
                            rest_url = "http://dlap30v:9002/gismart/search"
                            LOG.info("send status to development server")
                        elif args.test_server == False:
                            LOG.info("FIXME implement the production url")
                            LOG.info("send status to production server")
                        response = requests.post(rest_url, data=data_json, headers=headers)
                        print(response.status_code)
                        if response.status_code == requests.codes.ok:
                            LOG.info("Uploading {} completed successfully".format(sample_path))
                            LOG.info("JSON request was {}".format(data_json))
                            LOG.info("Response was {}".format(response.status_code))
                        else:
                            LOG.error("Uploading {} completed failed".format(sample_path))
            else:
                LOG.info("Bcl2fastq is not completed for {}".format(mux_dir))

if __name__ == "__main__":
    LOG.info("STATS update starting")
    main()
    LOG.info("Successful program exit")