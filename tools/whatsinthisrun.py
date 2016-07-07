#!/usr/bin/env python3
"""Print information about sequencing run
"""
import os
import sys
import requests

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from rest import rest_services

def main(run_num):
    """main function
    """
    rest_url = rest_services['run_details']['testing'].replace("run_num", run_num)
    r = requests.get(rest_url)
    if r.status_code != requests.codes.ok:
        r.raise_for_status()

    get_data = r.json()
    # if runId missing assume wrong run number
    if 'runId' not in get_data:
        sys.stderr.write("FATAL: Run number not found in ELM\n")
        sys.exit(1)

    for rows in get_data['lanes']:
        if "MUX" in rows['libraryId']:
            for child in rows['Children']:
                sample = (get_data['runId'], rows['laneId'], rows['libraryId'], '\tNA', child['barcode'], child['genome'], child['libraryId'], child['libtech'], child['Analysis'])
                print('\t'.join(sample))
        else:
            sample = (run_num, rows['laneId'], rows['libraryId'], rows['genome'], rows['libtech'], rows['Analysis'])
            print('\t'.join(sample))

if __name__ == "__main__":
    # FIXME:add-argparser
    if len(sys.argv) != 2:
        sys.stderr.write("FATAL: need exactly only run id\n")
        sys.exit(1)
    run_num = sys.argv[1]
    main(run_num)

