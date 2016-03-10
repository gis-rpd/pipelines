#!/usr/bin/env python3
"""Sample Sheet generation for BCL2FASTQ pipeline
"""
# --- standard library imports
#
import sys
import os
import logging
import argparse
from datetime import datetime

#--- third-party imports
#
import yaml
import requests
import xml.etree.ElementTree as ET

#--- project specific imports
# /


# global logger
# http://docs.python.org/library/logging.html
LOG = logging.getLogger("")
logging.basicConfig(level=logging.INFO,
                    format='%(levelname)s [%(asctime)s]: %(message)s')


SAMPLESHEET_HEADER = '[Data]'+'\n'+ 'Lane,Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,I5_Index_ID,index2,Sample_Project,Description'

   
    
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
    parser.add_argument("-r", "--runIDPath",
                        dest="runIDPath",
                        required=True,
                        help="runIDPath, e.g. /mnt/seq/userrig/HS004/HS004-PE-R00139_BC6A7HANXX")
    parser.add_argument("-o", "--outdir",
                        required=True,
                        dest="outdir",
                        help="output directory, e.g.  /mnt/projects/rpd/testing/output/bcl2fastq ")
    return parser
   
def getdirs(args):
    runIDPath = args.runIDPath
    if not os.path.exists(runIDPath):
        LOG.fatal("runIDPath '%s' does not exist under Run directory.\n" % (runIDPath))
        sys.exit(1)
    
    RunInfo = os.path.join(args.runIDPath + '/RunInfo.xml')
    if not os.path.exists(RunInfo):
        LOG.fatal("RunInfo '%s' does not exist under Run directory.\n" % (RunInfo))
        sys.exit(1)  
        
    outdir = args.outdir    
    if not os.path.exists(outdir):
        LOG.fatal("output directory '%s' does not exist.\n" % (outdir))
        sys.exit(1)
        
    return(runIDPath,outdir,RunInfo)

def generateUseBases(barcode_lens, RunInfo):
    tree = ET.parse(RunInfo)
    root = tree.getroot()   
    UB_list = []
    
    # for each lane and its barcode lengths
    for k, v in sorted(barcode_lens.items()):
        # v is list of barcode_len tuples
        assert len(set(v))==1, ("Different barcode length in lane {}".format(k))
        BC1, BC2 = v[0]# since all v's are the same
        
        UB = ""
        #if test:
        for Read in root.iter('Read'):
            NumCyc = int(Read.attrib['NumCycles'])-1
            if Read.attrib['IsIndexedRead'] == 'N':
                UB+='Y'+str(NumCyc)+'n*,'  
            elif Read.attrib['IsIndexedRead'] == 'Y':
                if Read.attrib['Number'] == '2':    ### BC1
                    if BC1 > 0:
                        UB+='I'+str(BC1)+'n*,'
                    else:
                        UB+='n*'+','
                if Read.attrib['Number'] == '3':    ### BC2
                    if BC2 > 0:
                        UB+='I'+str(BC2)+'n*,'
                    else:
                        UB+='n*'+','
        UB = UB[:-1]
        UB_list.append(str(k+':'+UB)) 
    return (UB_list)
 
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
        
    (runIDPath,outdirbase,RunInfo) = getdirs(args)
    runid_with_flowcellid = runIDPath.split('/')[-1]
    flowcellid = runid_with_flowcellid.split('_')[-1]
    machine_id = runid_with_flowcellid.split('-')[0]
    
    # keys: lanes, values are barcode lens in lane (always two tuples, -1 if not present)
    barcode_lens = {}
    sample_info = []
    LOG.info("Generating sample sheet")
    run_num = runid_with_flowcellid.split('_')[0]
    
    #rest_url = 'http://dlap51v:8080/elm/rest/seqrun/illumina/' + run_num + '/detailanalysis/json'
    rest_url = 'http://qldb01:8080/rest/seqrun/illumina/' + run_num + '/detailanalysis/json'
    response = requests.get(rest_url)
    rest_data = response.json()

    outdir = os.path.join(outdirbase, machine_id,
                            runid_with_flowcellid + '_' + generate_timestamp())
    assert not os.path.exists(outdir)
    os.makedirs(outdir)    
    run_id = rest_data['runId']
    counter = 0
    if rest_data['runPass'] != 'Pass':
        LOG.info("Skipping non-passed run")
        sys.exit(0)     
    # this is the master samplesheet
    samplesheet = os.path.join(outdir, run_id + '_sampleSheet.csv')
    with open(samplesheet, 'w') as fh_out:
        fh_out.write(SAMPLESHEET_HEADER + '\n') 
        for rows in rest_data['lanes']:
            if rows['lanePass'] == 'Pass':
                if "MUX" in rows['libraryId']:
                    # multiplexed
                    counter = 0
                    for child in rows['Children']:
                        counter += 1
                        id = 'S'+str(counter)
                        if "-" in (child['barcode']):
                            # dual index  
                            index = child['barcode'].split('-')
                            sample = rows['laneId']+',Sample_'+child['libraryId']+','+child['libraryId']+'-'+child['barcode']+',,,'+id+','+ index[0] +',,'+ index[1] + ',' +'Project_'+rows['libraryId']+','+child['libtech']
                            index_lens = (len((index[0])), len((index[1])))
                            sample_dir = os.path.join(outdir, machine_id, + 'Project_' + rows['libraryId']+','+ 'Sample_' + child['libraryId'])
                            #print ('TEST' + sample_dir)
                            sample_dir = outdir + '/' + machine_id + '/' + 'Project_' + rows['libraryId'] + 'Sample_' + child['libraryId']
                            sample_id = run_id + ',' + flowcellid + ',' + child['libraryId'] + ',' + rows['laneId'] + ',' + sample_dir
                            print (sample_id)
           
                        else:	
                            sample = rows['laneId']+',Sample_'+child['libraryId']+','+child['libraryId']+'-'+child['barcode']+',,,'+id+','+child['barcode']+',,,'+'Project_'+rows['libraryId']+','+child['libtech']
                            index_lens = (len(child['barcode']), -1)
                            sample_dir = outdir + '/' + machine_id + '/' + 'Project_' + rows['libraryId'] + 'Sample_' + child['libraryId']
                            sample_id = run_id + ',' + flowcellid + ',' + child['libraryId'] + ',' + rows['laneId']+ ',' + sample_dir
                            print (sample_id)
                        
                        sample_info.append(sample_id) 
                        barcode_lens.setdefault(rows['laneId'], []).append(index_lens)
                        fh_out.write(sample+ '\n') 
                else:
                    # non-multiplexed
                    sample = rows['laneId']+',Sample_'+rows['libraryId']+','+rows['libraryId']+'-NoIndex'+',,,,,,,'+'Project_'+rows['libraryId']+','+rows['libtech']
                    index_lens = (-1, -1)
                    barcode_lens.setdefault(rows['laneId'], []).append(index_lens)
                    sample_dir = outdir + '/' + machine_id + '/' + 'Project_' + rows['libraryId'] + 'Sample_' + rows['libraryId']
                    sample_id = run_id + ',' + flowcellid + ',' + child['libraryId'] + ',' + rows['laneId']+ ',' + sample_dir
                    sample_info.append(sample_id) 
                    fh_out.write(sample+ '\n') 
    LOG.info("Generating UseBases")
    UseBases = generateUseBases(barcode_lens, RunInfo)
    UseBases_data = dict(UseBases = UseBases )
    
    config_useBase = os.path.join(outdir,run_id + '_useBases.yaml')
    with open(config_useBase, 'w') as outfile:
        outfile.write( yaml.dump(UseBases_data, default_flow_style=True))
    
    sample_info_yaml = dict(sample_info = sample_info )
    config_sample_info = os.path.join(outdir,run_id + '_sampleInfo.yaml')
    with open(config_sample_info, 'w') as outfile:
        outfile.write( yaml.dump(sample_info_yaml, default_flow_style=True))
        
if __name__ == "__main__":
    main()
    LOG.info("Successful program exit")
