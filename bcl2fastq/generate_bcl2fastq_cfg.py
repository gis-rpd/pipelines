#!/usr/bin/env python3
"""Sample Sheet generation for BCL2FASTQ pipeline
"""
# --- standard library imports
#
import sys
import os
import logging
import argparse
from collections import namedtuple

#--- third-party imports
#
import yaml
import requests
import xml.etree.ElementTree as ET

#--- project specific imports
#
from pipelines import get_machine_run_flowcell_id
# cannot be imported? from bcl2fastq import MuxUnit
MuxUnit = namedtuple('MuxUnit', ['run_id', 'flowcell_id', 'mux_id', 'lane_id', 'mux_dir', 'barcode_mismatches'])


__author__ = "Lavanya Veeravalli"
__email__ = "veeravallil@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# global logger
# http://docs.python.org/library/logging.html
LOG = logging.getLogger("")
logging.basicConfig(level=logging.INFO,
                    format='%(levelname)s [%(asctime)s]: %(message)s')


SAMPLESHEET_CSV = "samplesheet.csv"
USEBASES_CFG = "usebases.yaml"
MUXINFO_CFG = "muxinfo.yaml"

SAMPLESHEET_HEADER = '[Data]'+'\n'+ 'Lane,Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,I5_Index_ID,index2,Sample_Project,Description'


def cmdline_parser():
    """
    creates a argparse instance
    """

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("-v", "--verbose",
                        action="store_true",
                        help="Be verbose")
    parser.add_argument("--debug",
                        action="store_true",
                        help="Enable debugging")
    parser.add_argument("--force-overwrite",
                        action="store_true",
                        help="Force overwriting of output files")
    parser.add_argument("-r", "--runIDPath",
                        dest="runIDPath",
                        required=True,
                        help="runIDPath, e.g. /mnt/seq/userrig/HS004/HS004-PE-R00139_BC6A7HANXX")
    parser.add_argument("-o", "--outdir",
                        required=True,
                        dest="outdir",
                        help="Output directory")
    return parser


def getdirs(args):
    """gets directories from args and checks existance
    """
    runidpath = args.runIDPath
    if not os.path.exists(runidpath):
        LOG.fatal("runIDPath '%s' does not exist under Run directory.\n" % (runidpath))
        sys.exit(1)

    runinfo = os.path.join(runidpath + '/RunInfo.xml')
    if not os.path.exists(runinfo):
        LOG.fatal("RunInfo '%s' does not exist under Run directory.\n" % (runinfo))
        sys.exit(1)

    outdir = args.outdir
    if not os.path.exists(outdir):
        LOG.fatal("output directory '%s' does not exist.\n" % (outdir))
        sys.exit(1)

    return(runidpath, outdir, runinfo)


def generate_usebases(barcode_lens, runinfo):
    """FIXME:add-doc
    """
    tree = ET.parse(runinfo)
    root = tree.getroot()
    ub_list = []

    # for each lane and its barcode lengths
    for k, v in sorted(barcode_lens.items()):
        # v is list of barcode_len tuples
        assert len(set(v)) == 1, ("Different barcode length in lane {}".format(k))
        bc1, bc2 = v[0]# since all v's are the same

        ub = ""
        #if test:
        for read in root.iter('Read'):
            numcyc = int(read.attrib['NumCycles'])-1
            if read.attrib['IsIndexedRead'] == 'N':
                ub += 'Y' + str(numcyc) + 'n*,'
            elif read.attrib['IsIndexedRead'] == 'Y':
                if read.attrib['Number'] == '2':    ### BC1
                    if bc1 > 0:
                        ub += 'I'+str(bc1)+'n*,'
                    else:
                        ub += 'n*'+','
                if read.attrib['Number'] == '3':    ### BC2
                    if bc2 > 0:
                        ub += 'I'+str(bc2)+'n*,'
                    else:
                        ub += 'n*'+','
        ub = ub[:-1]
        ub_list.append(str(k + ':' + ub))
    return ub_list


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

    (runidpath, outdir, runinfo) = getdirs(args)
    samplesheet_csv = os.path.join(outdir, SAMPLESHEET_CSV)
    usebases_cfg = os.path.join(outdir, USEBASES_CFG)
    muxinfo_cfg = os.path.join(outdir, MUXINFO_CFG)
    for f in [samplesheet_csv, usebases_cfg, muxinfo_cfg]:
        if not args.force_overwrite and os.path.exists(f):
            LOG.fatal("Refusing to overwrite existing file {}".format(f))
            sys.exit(1)

    runid_with_flowcellid = runidpath.rstrip("/").split('/')[-1]
    _machine_id, run_num, flowcellid = get_machine_run_flowcell_id(runid_with_flowcellid)

    LOG.info("Querying ELM for {}".format(run_num))
    #rest_url = 'http://dlap51v:8080/elm/rest/seqrun/illumina/' + run_num + '/detailanalysis/json'
    rest_url = 'http://qldb01:8080/rest/seqrun/illumina/' + run_num + '/detailanalysis/json'
    response = requests.get(rest_url)
    if response.status_code != requests.codes.ok:
        response.raise_for_status()
    rest_data = response.json()

    run_id = rest_data['runId']
    counter = 0
    if rest_data['runPass'] != 'Pass':
        LOG.info("Skipping non-passed run")
        sys.exit(0)

    # this is the master samplesheet
    LOG.info("Writing to {}".format(samplesheet_csv))
    # keys: lanes, values are barcode lens in lane (always two tuples, -1 if not present)
    barcode_lens = {}
    mux_units = []
    with open(samplesheet_csv, 'w') as fh_out:
        fh_out.write(SAMPLESHEET_HEADER + '\n')
        for rows in rest_data['lanes']:
            if rows['lanePass'] == 'Pass':
                if "MUX" in rows['libraryId']:
                    # multiplexed
                    counter = 0
                    for child in rows['Children']:
                        counter += 1
                        id = 'S' + str(counter)
                        if "-" in child['barcode']:
                            # dual index
                            index = child['barcode'].split('-')
                            sample = rows['laneId']+',Sample_'+child['libraryId']+','+child['libraryId']+'-'+child['barcode']+',,,'+id+','+ index[0] +',,'+ index[1] + ',' +'Project_'+rows['libraryId']+','+child['libtech']
                            index_lens = (len((index[0])), len((index[1])))
                        else:
                            sample = rows['laneId']+',Sample_'+child['libraryId']+','+child['libraryId']+'-'+child['barcode']+',,,'+id+','+child['barcode']+',,,'+'Project_'+rows['libraryId']+','+child['libtech']
                            index_lens = (len(child['barcode']), -1)
                        barcode_lens.setdefault(rows['laneId'], []).append(index_lens)

                else:# non-multiplexed
                    sample = rows['laneId']+',Sample_'+rows['libraryId']+','+rows['libraryId']+'-NoIndex'+',,,,,,,'+'Project_'+rows['libraryId']+','+rows['libtech']
                    index_lens = (-1, -1)
                    barcode_lens.setdefault(rows['laneId'], []).append(index_lens)

                barcode_mismatches = 1
                muxunit = MuxUnit._make([run_id, flowcellid, rows['libraryId'], rows['laneId'], 'Project_' + rows['libraryId'], barcode_mismatches])
                mux_units.append(muxunit)
                fh_out.write(sample + '\n')
    LOG.warn("get barcode_mismatches from ELM (see above)")

    LOG.warn("What if MUX is spread across multiple lanes? lanes need to be merged into list for this MUX")
    LOG.info("Writing to {}".format(usebases_cfg))
    usebases = generate_usebases(barcode_lens, runinfo)
    with open(usebases_cfg, 'w') as fh:
        fh.write(yaml.dump(dict(usebases=usebases), default_flow_style=True))

    LOG.info("Writing to {}".format(muxinfo_cfg))
    with open(muxinfo_cfg, 'w') as fh:
        fh.write(yaml.dump([dict(mu._asdict()) for mu in mux_units], default_flow_style=True))


if __name__ == "__main__":
    main()
    LOG.info("Successful program exit")
