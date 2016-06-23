#!/usr/bin/env python3
"""Print information about sequencing run
"""

import sys
import requests


def main(run_num):
    """main function
    """

    run_url = 'http://plap18v:8080/rest/seqrun/illumina/' + run_num + '/detailanalysis/json'
    #print(run_url)
    r = requests.get(run_url)
    if r.status_code != requests.codes.ok:
        r.raise_for_status()

    get_data = r.json()
    # if runId missing assume wrong run number
    if 'runId' not in get_data:
        sys.stderr.write("FATAL: Run number not found in ELM\n")
        sys.exit(1)

    #run_id = get_data['runId']
    #print(run_id)
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
    main(sys.argv[1])
