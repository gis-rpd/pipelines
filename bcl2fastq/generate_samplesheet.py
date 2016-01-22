#!/usr/bin/env python3
"""Sample Sheet generation for BCL2FASTQ pipeline
"""

# --- standard library imports
#
import sys
import os
#import time
import logging
#import json
import argparse
from datetime import datetime

#--- third-party imports
#
import yaml
import requests

#--- project specific imports
# /


# global logger
# http://docs.python.org/library/logging.html
LOG = logging.getLogger("")
logging.basicConfig(level=logging.INFO,
                    format='%(levelname)s [%(asctime)s]: %(message)s')



SAMPLESHEET_HEADER = 'Lane,Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,I5_Index_ID,index2,Sample_Project,Description'


def generate_timestamp():
    """generate ISO8601 timestamp incl microsends
    """
    return datetime.isoformat(datetime.now())


def cmdline_parser():
    """
    creates a argparse instance
    """

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("-v", "--verbose",
                        action="store_true", dest="verbose",
                        help="be verbose")
    parser.add_argument("--debug",
                        action="store_true", dest="debug",
                        help="debugging")
    parser.add_argument("-r", "--runID",
                        dest="runid_with_flowcellid",
                        required=True,
                        help="run-id with flowcell-id, e.g. HS006-SR-R00012_AHFLKGBCXX")
    parser.add_argument("-c", "--config",
                        required=True,
                        dest="config",
                        help="Config file (yaml)")# FIXME add doc. config needed for just two params?
    return parser


def main():
    """
    The main function
    """
    parser = cmdline_parser()
    args = parser.parse_args()

    if args.verbose:
        LOG.setLevel(logging.INFO)
    if args.debug:
        LOG.setLevel(logging.DEBUG)


    # FIXME function getdirs()
    if not os.path.exists(args.config):
        LOG.fatal("config file '%s' does not exist.\n" % args.config)
        sys.exit(1)
    with open(args.config, 'r') as ymlfile:
        try:
            cfg = yaml.load(ymlfile)
        except:
            LOG.fatal("Couldn't parse {}. Are you sure this is a valid YAML file?".format(ymlfile.name))
            raise

    try:
        assert 'dir' in cfg['dir']
        assert 'input' in cfg['dir']
        assert 'output' in cfg['dir']
    except AssertionError:
        LOG.fatal("Missing required keys from config file {}".format(ymlfile.name))
        sys.exit(1)

    # FIXME inputdir not used
    inputdir = os.path.join(cfg['dir']['input'], args.runid_with_flowcellid)
    outputdir = cfg['dir']['output']
    if not os.path.exists(inputdir):
        LOG.fatal("Input directory '%s' does not exist.\n" % (inputdir))
        sys.exit(1)
    if not os.path.exists(outputdir):
        LOG.fatal("output directory '%s' does not exist.\n" % (outputdir))
        sys.exit(1)
    # FIXME end function getdirs()


    machine_id = args.runid_with_flowcellid.split('-')[0]
    sample_dict = {}
    run_num = args.runid_with_flowcellid.split('_')[0]
    rest_url = 'http://qldb01:8080/rest/seqrun/illumina/' + run_num + '/detailanalysis/json'
    response = requests.get(rest_url)
    data = response.json()
    # FIXME check that required keys are there

    
    path = os.path.join(outputdir, machine_id,
                        args.runid_with_flowcellid + '_' + generate_timestamp())
    assert not os.path.exists(path)
    os.makedirs(path)
    run_id = data['runId']
    counter = 0
    # we made sure output directory doesn't exist so samplesheets
    # cannot exist by definition
    if data['runPass'] == 'Pass':
        # this is the master samplesheet
        samplesheet = os.path.join(path + '/' + run_id + '_sampleSheet.csv')
        with open(samplesheet, 'w') as fh_out:
            fh_out.write(SAMPLESHEET_HEADER + '\n')
            for rows in data['lanes']:
                if rows['lanePass'] == 'Pass':
                    if "MUX" in rows['libraryId']:
                        counter = 0
                        for child in rows['Children']:
                            counter += 1
                            id = 'S'+str(counter)
                            barcode_len=len(child['barcode'])
                            sample = rows['laneId']+',Sample_'+child['libraryId']+','+child['libraryId']+'-'+child['barcode']+',,,'+id+','+child['barcode']+',,,'+'Project_'+child['libraryId']+','+child['libtech']
                            sample_dict.setdefault(barcode_len, []).append(sample)
                            fh_out.write(sample+ '\n')
                    else:
                        sample = rows['laneId']+',Sample_'+rows['libraryId']+','+rows['libraryId']+'-NoIndex'+',,,,,,,'+'Project_'+rows['libraryId']+','+rows['libtech']
                        sample_dict.setdefault('0', []).append(sample)
                        fh_out.write(sample+ '\n')

    for k, v in sample_dict.items():
        # samplesheet per index
        samplesheet = os.path.join(path, + run_id + '_index' + str(k) + '_sampleSheet.csv')
        with open(samplesheet) as fh_out:
            fh_out.write(SAMPLESHEET_HEADER +'\n')
            for i in range(len(v)):
                fh_out.write(v[i]+ '\n')


if __name__ == "__main__":
    main()
    LOG.info("Successful program exit")
