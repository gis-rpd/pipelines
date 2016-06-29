#!/usr/bin/env python3
"""Print sequencing run information that contain given library
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

def main(lib_id):
    """main function"""
    rest_url = rest_services['lib_details']['production'].replace("lib_id", lib_id)
    r = requests.get(rest_url)
    if r.status_code != requests.codes.ok:
        r.raise_for_status()

    get_data = r.json()
    if 'libraryId' not in get_data:
        sys.stderr.write("FATAL: Library id not found in ELM\n")
        sys.exit(1)

    for rows in get_data['runs']:
        if "MUX" in get_data['libraryId']:
            for child in rows['lanes']:
                sample = (rows['runId'], child['laneId'], get_data['libraryId'], '\tNA', get_data['multiplexKit'])
                print('\t'.join(sample))
        else:
            for child in rows['lanes']:
                sample = (rows['runId'], child['laneId'], get_data['libraryId'], child['genome'], get_data['type'], get_data['organism'], get_data['tissueType'], get_data['sample_location'], get_data['target'], get_data['antibody'], get_data['control'], get_data['description'])
                print('\t'.join(sample))
                
if __name__ == "__main__":
    # FIXME:add-argparser
    if len(sys.argv) != 2:
        sys.exit("FATAL: need exactly one library id")
    lib_id = sys.argv[1]
    main(lib_id)
