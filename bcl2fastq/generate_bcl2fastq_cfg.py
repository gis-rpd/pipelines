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
import xml.etree.ElementTree as ET

#--- third-party imports
#
import requests
import yaml

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from config import rest_services
from config import bcl2fastq_conf
from pipelines import get_machine_run_flowcell_id
from pipelines import email_for_user
from pipelines import send_mail
from pipelines import is_devel_version
from pipelines import user_mail_mapper

# WARNING changes here, must be reflected in bcl2fastq.py as well
MuxUnit = namedtuple('MuxUnit', ['run_id', 'flowcell_id', 'mux_id', 'lane_ids',
                                 'mux_dir', 'barcode_mismatches', 'requestor_email',
                                 'samplesheet', 'bcl2fastq_custom_args'])

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

SAMPLESHEET_CSV = "*samplesheet.csv"
MUXINFO_CFG = "muxinfo.yaml"
STATUS_CFG = "status.txt"
DEFAULT_BARCODE_MISMATCHES = None

SAMPLESHEET_HEADER = '[Data]'+'\n'+ 'Lane,Sample_ID,Sample_Name,Sample_Plate,' \
    'Sample_Well,I7_Index_ID,index,I5_Index_ID,index2,Sample_Project,Description'

def getdirs(args):
    """gets directories from args and checks existance
    """
    rundir = args.rundir
    if not os.path.exists(rundir):
        logger.fatal("rundir '%s' does not exist under Run directory.\n", rundir)
        sys.exit(1)
    runinfo = os.path.join(rundir + '/RunInfo.xml')
    if not os.path.exists(runinfo):
        logger.fatal("RunInfo '%s' does not exist under Run directory.\n", runinfo)
        sys.exit(1)
    outdir = args.outdir
    if not os.path.exists(outdir):
        logger.fatal("output directory '%s' does not exist.\n", outdir)
        sys.exit(1)
    return(rundir, outdir, runinfo)

def email_non_bcl(libraryId, runId):
    """send email for non-bcl libraries
    """
    if is_devel_version():
        toaddr = email_for_user()
    else:
        toaddr = "rpd@gis.a-star.edu.sg"
    subject = "bcl2fastq conversion not required for {} from run {}.".format(
        libraryId, runId)
    body = subject + "\n" + "Kindly start custom analysis manually. Thanks."
    send_mail(subject, body, toaddr=toaddr, pass_exception=False)

def get_ub_str_index(ub, create_index, bc, non_mux_tech, libraryId):
    """use_bases for index reads
    """
    if create_index:
        if bc > 0:
            ub += 'I'+str(bc)+'n*,'
        elif bc < 0:
            if non_mux_tech or "MUX" not in libraryId:
                ub += 'I*' + ','
            else:
                ub += 'n*' + ','
    else:
        if bc > 0:
            ub += 'I'+str(bc)+'n*,'
        else:
            ub += 'n*'+','
    return ub

def generate_usebases(barcode_lens, runinfo, create_index, non_mux_tech, libraryId):
    """generate use_bases param
    """
    tree = ET.parse(runinfo)
    root = tree.getroot()
    ub_list = dict()
    readLength_list = []
    # for each lane and its barcode lengths
    for k, v in sorted(barcode_lens.items()):
        # v is list of barcode_len tuples
        assert len(set(v)) == 1, ("Different barcode length in lane {}".format(k))
        bc1, bc2 = v[0]# since all v's are the same
        ub = ""
        for read in root.iter('Read'):
            numcyc = int(read.attrib['NumCycles'])
            if read.attrib['IsIndexedRead'] == 'N':
                ub += 'Y*,'
                readLength_list.append(numcyc)
            elif read.attrib['IsIndexedRead'] == 'Y':
                if read.attrib['Number'] == '2':   ### BC1
                    ub = get_ub_str_index(ub, create_index, bc1, non_mux_tech, libraryId)
                elif read.attrib['Number'] == '3':    ### BC2
                    ub = get_ub_str_index(ub, create_index, bc2, non_mux_tech, libraryId)
        ub = ub[:-1]
        ub_list[k] = ub
    return ub_list, readLength_list

def get_rest_data(run_num, test_server=None):
    """ Get rest info from ELM
    """
    if test_server:
        rest_url = rest_services['run_details']['testing'].replace("run_num", run_num)
        logger.info("development server")
    else:
        rest_url = rest_services['run_details']['production'].replace("run_num", run_num)
        logger.info("production server")
    response = requests.get(rest_url)
    if response.status_code != requests.codes.ok:
        response.raise_for_status()
        sys.exit(1)
    rest_data = response.json()
    logger.debug("rest_data from %s: %s", rest_url, rest_data)
    return rest_data

def generate_samplesheet(rest_data, flowcellid, outdir, runinfo):
    """Generates sample sheet, mux_info and bcl2fastq custom params
    """
    barcode_lens = {}
    mux_units = dict()
    lib_list = dict()
    run_id = rest_data['runId']
    muxinfo_cfg = os.path.join(outdir, MUXINFO_CFG)
    non_mux_tech = False
    for rows in rest_data['lanes']:
        BCL_Mismatch = []
        if 'requestor' in rows:
            requestor = rows['requestor']
            requestor_email = user_mail_mapper(requestor)
        else:
            requestor_email = None
        pass_bcl2_fastq = False
        #MUX library
        if "MUX" in rows['libraryId']:
            for child in rows['Children']:
                if 'BCL_Mismatch' in child:
                    BCL_Mismatch.append(child['BCL_Mismatch'])
                if any(libtech in child['libtech'] for libtech in bcl2fastq_conf['non_bcl_tech']):
                    logger.info("send_mail: bcl not required for %s", rows['libraryId'])
                    email_non_bcl(rows['libraryId'], rest_data['runId'])
                    pass_bcl2_fastq = True
                    break
                if any(libtech in child['libtech'] for libtech in bcl2fastq_conf['non_mux_tech']):
                    sample = rows['laneId']+',Sample_'+rows['libraryId']+','+rows['libraryId']+ \
                        '-NoIndex'+',,,,,,,'+'Project_'+rows['libraryId']+','+child['libtech']
                    lib_list.setdefault(rows['libraryId'], []).append(sample)
                    index_lens = (-1, -1)
                    non_mux_tech = True
                    barcode_lens.setdefault(rows['laneId'], []).append(index_lens)
                    break
                if "-" in child['barcode']:
                    # dual index
                    index = child['barcode'].split('-')
                    sample = rows['laneId']+',Sample_'+child['libraryId']+','+ \
                        child['libraryId']+'-'+child['barcode']+',,,,'+ index[0] +',,'+ \
                        index[1] + ',' +'Project_'+rows['libraryId']+','+child['libtech']
                    index_lens = (len((index[0])), len((index[1])))
                else:
                    sample = rows['laneId']+',Sample_'+child['libraryId']+','+ \
                        child['libraryId']+'-'+child['barcode']+',,,,'+child['barcode']+',,,'\
                        +'Project_'+rows['libraryId']+','+child['libtech']
                    index_lens = (len(child['barcode']), -1)
                barcode_lens.setdefault(rows['laneId'], []).append(index_lens)
                lib_list.setdefault(rows['libraryId'], []).append(sample)
        else:
            #Non-mux library
            if rows['libtech'] in bcl2fastq_conf['non_bcl_tech']:
                logger.info("send_mail: bcl not required for %s", rows['libraryId'])
                email_non_bcl(rows['libraryId'], rest_data['runId'])
                pass_bcl2_fastq = True
                continue
            sample = rows['laneId']+',Sample_'+rows['libraryId']+','+rows['libraryId']+ \
                    '-NoIndex'+',,,,,,,'+'Project_'+rows['libraryId']+','+rows['libtech']
            lib_list.setdefault(rows['libraryId'], []).append(sample)
            index_lens = (-1, -1)
            barcode_lens.setdefault(rows['laneId'], []).append(index_lens)
        if pass_bcl2_fastq:
            continue
        #Barcode mismatch has to be the same for all the libraries in one MUX.
        #Otherwise default mismatch value to be used
        if len(set(BCL_Mismatch)) == 1:
            barcode_mismatches = BCL_Mismatch[0]
        else:
            barcode_mismatches = DEFAULT_BARCODE_MISMATCHES
        #Check adpter trimming
        if 'trimadapt' in rows and rows['trimadapt']:
            lib_list.setdefault(rows['libraryId'], []).append('[Settings]')
            adapt_seq = rows.get('adapterseq').split(',')
            for seq in adapt_seq:
                reads = seq.split(':')
                if reads[0].strip() == "Read 1":
                    adapter = "Adapter," + reads[1].lstrip()
                    lib_list.setdefault(rows['libraryId'], []).append(adapter)
                elif reads[0].strip() == "Read 2":
                    adapter = "AdapterRead2," + reads[1].lstrip()
                    lib_list.setdefault(rows['libraryId'], []).append(adapter)
        samplesheet = os.path.abspath(os.path.join(outdir, rows['libraryId'] + "_samplesheet.csv"))
        create_index = False
        if 'indexreads' in rows and rows['indexreads']:
            create_index = True
        usebases, readLength_list = generate_usebases(barcode_lens, runinfo, create_index, non_mux_tech, rows['libraryId'])
        use_bases_mask = " --use-bases-mask " + rows['laneId'] + ":" + usebases[rows['laneId']]
        bcl2fastq_custom_args = use_bases_mask
        if 'indexreads' in rows and rows['indexreads']:
            bcl2fastq_custom_args = " ".join([bcl2fastq_custom_args, \
                                        bcl2fastq_conf['bcl2fastq_custom_args']['indexreads']])
        readLength_list.sort()
        #if barcode_lens:
        del barcode_lens[rows['laneId']]
        #bcl2fastq_custom_args to be added if any of the R1 or R2 less than minReadLength
        if readLength_list[0] < bcl2fastq_conf['minReadLength']:
            minReadLength_params = bcl2fastq_conf['bcl2fastq_custom_args']['minReadLength']
            param_a = " " + minReadLength_params[0] + " " + str(readLength_list[0])
            param_b = " " + minReadLength_params[1] + " 0"
            bcl2fastq_custom_args += param_a
            bcl2fastq_custom_args += param_b
        mu = MuxUnit._make([run_id, flowcellid, rows['libraryId'], [rows['laneId']], \
            'Project_'+ rows['libraryId'], barcode_mismatches, requestor_email, samplesheet, \
            [bcl2fastq_custom_args]])
        # merge lane into existing mux if needed
        if mu.mux_id in mux_units:
            mu_orig = mux_units[mu.mux_id]
            assert mu.barcode_mismatches == mu_orig.barcode_mismatches
            assert len(mu.lane_ids) == 1# is a list by design but just one element.
            #otherwise below fails
            lane_ids = mu_orig.lane_ids.extend(mu.lane_ids)
            bcl2fastq_custom_args = mu_orig.bcl2fastq_custom_args.append(use_bases_mask)
            mu_orig = mu_orig._replace(lane_ids=lane_ids, bcl2fastq_custom_args= \
                                    bcl2fastq_custom_args)
        else:
            mux_units[mu.mux_id] = mu
    #Write muxinfo_cfg and Samplesheet
    if mux_units:
        with open(muxinfo_cfg, 'w') as fh:
            fh.write(yaml.dump([dict(mu._asdict()) for mu in mux_units.values()], \
            default_flow_style=True))
        for lib, value in lib_list.items():
            csv = mux_units[lib].samplesheet
            with open(csv, 'w') as fh_out:
                fh_out.write(SAMPLESHEET_HEADER + '\n')
                for each in value:
                    fh_out.write(each+ '\n')
        return True
    else:
        return False

def main():
    """
    The main function
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force-overwrite",
                        action="store_true",
                        help="Force overwriting of output files")
    parser.add_argument("-r", "--rundir",
                        dest="rundir",
                        required=True,
                        help="rundir, e.g. /mnt/seq/userrig/HS004/HS004-PE-R00139_BC6A7HANXX")
    parser.add_argument('-t', "--test-server", action='store_true')
    parser.add_argument("-o", "--outdir",
                        required=True,
                        dest="outdir",
                        help="Output directory")
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

    (rundir, outdir, runinfo) = getdirs(args)
    samplesheet_csv = os.path.join(outdir, SAMPLESHEET_CSV)
    muxinfo_cfg = os.path.join(outdir, MUXINFO_CFG)
    for f in [samplesheet_csv, muxinfo_cfg]:
        if not args.force_overwrite and os.path.exists(f):
            logger.fatal("Refusing to overwrite existing file %s", f)
            sys.exit(1)
    _, run_num, flowcellid = get_machine_run_flowcell_id(rundir)
    logger.info("Querying ELM for %s", run_num)
    rest_data = get_rest_data(run_num, args.test_server)
    status_cfg = os.path.join(outdir, STATUS_CFG)
    assert rest_data['runId'], ("Rest data from ELM does not have runId {}".format(run_num))
    if rest_data['runPass'] != 'Pass':
        logger.warning("Skipping non-passed run")
        with open(status_cfg, 'w') as fh_out:
            fh_out.write("SEQRUNFAILED")
        sys.exit(0)
    status = generate_samplesheet(rest_data, flowcellid, outdir, runinfo)
    if not status:
        with open(status_cfg, 'w') as fh_out:
            fh_out.write("NON-BCL")

if __name__ == "__main__":
    main()
    logger.info("Successful program exit")
