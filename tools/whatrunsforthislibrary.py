#!/usr/bin/env python3
"""Print sequencing run information that contain given library
"""

import sys
import requests


def main(library_id):
    """main function"""

    run_url = 'http://plap18v:8080/rest/libinfo/' + library_id + '/solexaRun/json'
    r = requests.get(run_url)
    if r.status_code != requests.codes.ok:
        r.raise_for_status()

    get_data = r.json()
    if 'libraryId' not in get_data:
        sys.stderr.write("FATAL: Library id not found in ELM\n")
        sys.exit(1)

    run_id = get_data['libraryId']
    print(run_id)

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
    library_id = sys.argv[1]
