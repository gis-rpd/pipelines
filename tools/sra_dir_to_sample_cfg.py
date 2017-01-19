#!/usr/bin/env python3
"""Write a sample config for a given directory containing fastq files
following SRA naming conventions
"""

#--- standard library imports
#
import glob
import re
import os
import sys
import argparse
import logging

#--- third-party imports
#
import yaml

# --- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(os.path.join(os.path.dirname(
    os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from readunits import ReadUnit
from readunits import create_rg_id_from_ru
from readunits import key_for_readunit


__author__ = "Andreas WILM"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)


yaml.Dumper.ignore_aliases = lambda *args: True


def scheme_for_fastq(fastq):
    """
    Returns regexp matching auto determined fastq naming scheme

    From Chih Chuan 2016-10-26:
    We have 2 schemes, the Old H5 and the current CRAM.
    H5 Format :
    <runid>_<flowcell>_<barcode>.<library_id>_<laneid>_R[1|2].fastq.gz
    (AW: example actually showing a third also valid name:)
    HS003-PE-R00047_BC0HBTACXX.WSB100_TTAGGC_L003_R1.fastq.gz
    CRAM:
    <library_id>_<runid>_<laneid>_R[1|2].fastq
    WHH530_HS006-PE-R00021_L001_R1.fastq.gz

    """

    # sra naming schemes (use basename as input)
    schemes = dict()
    schemes['h5old'] = re.compile(
        r'(?P<run_id>[A-Za-z0-9-]+)_(?P<flowcell>[A-Za-z0-9-]+)\.(?P<library_id>[A-Za-z0-9-]+)_(?P<barcode>[A-Za-z0-9-]+)_L0*(?P<lane_id>[A-Za-z0-9-]+)_R(?P<read_no>[12]).fastq.gz')
    # schemes['h5new'] = re.compile(# FIXME MISSING
    schemes['cram'] = re.compile(# FIXME untested
        r'(?P<library_id>[A-Za-z0-9-]+)_(?P<run_id>[A-Za-z0-9-]+)_L0*(?P<lane_id>[A-Za-z0-9-]+)_R(?P<read_no>[12]).fastq.gz')

    scheme_re = None#pylint
    for scheme_name, scheme_re in schemes.items():
        match = scheme_re.match(os.path.basename(fastq))
        if match:
            logger.info("Matching scheme %s", scheme_name)
            break
    assert match, ("No matching scheme found for {}".format(fastq))
    return scheme_re


def readunits_for_sampledir(sampledir):
    """Turns fastq files in sampledir to readunits assuming they follow a
    valid SRA naming scheme

    """

    # determine naming scheme and loop through fastqs assuming fixed scheme
    fq1s = glob.glob(os.path.join(sampledir, "*R1.fastq.gz"))
    scheme = scheme_for_fastq(fq1s[0])
    readunits = dict()
    for fq1 in fq1s:
        match = scheme.search(os.path.basename(fq1))
        mgroups = match.groupdict()
        fq2 = fq1.replace("R1.fastq.gz", "R2.fastq.gz")
        if not os.path.exists(fq2):
            fq2 = None
        rg = None
        
        ru = ReadUnit(mgroups['run_id'],
                      mgroups.get('flowcell'),
                      mgroups['library_id'],
                      mgroups['lane_id'],
                      rg, fq1, fq2)
        ru = ru._replace(rg_id=create_rg_id_from_ru(ru))
        readunits[key_for_readunit(ru)] = dict(ru._asdict())
    return readunits


def sampledir_to_cfg(sampledir, samplecfg):
    """FIXME:add-doc
    """

    readunits = readunits_for_sampledir(sampledir)

    # in theory we could support multi sample in one dir. here we're being strict
    lib_ids = [ru['library_id'] for ru in readunits.values()]
    assert len(set(lib_ids)) == 1
    sample_name = lib_ids[0]
    samples = dict()
    samples[sample_name] = list(readunits.keys())

    # make fastq paths relativ to output
    for ru_key, ru in readunits.items():
        # read units are dicts here (not namedtuple)
        fq1 = ru['fq1']
        ru['fq1'] = os.path.relpath(fq1, start=os.path.dirname(samplecfg))
        fq2 = ru['fq2']
        if fq2:
            fq2 = os.path.relpath(fq2, start=os.path.dirname(samplecfg))
            ru['fq2'] = fq2
        # no need: readunits[ru_key] = ru

    with open(samplecfg, 'w') as fh:
        yaml.dump(dict(samples=samples), fh, default_flow_style=False)
        yaml.dump(dict(readunits=readunits), fh, default_flow_style=False)


def main():
    """main function"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-s', "--sampledir", required=True,
                        help="Sample directory containing fastq files, following any SRA naming convention")
    parser.add_argument('-o', "--samplecfg", required=True,
                        help="Output YAML files. FastQ file names will be relative to this file")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Increase verbosity")
    parser.add_argument('-q', '--quiet', action='count', default=0,
                        help="Decrease verbosity")
    args = parser.parse_args()
    
    # Repeateable -v and -q for setting logging level.
    # See https://www.reddit.com/r/Python/comments/3nctlm/what_python_tools_should_i_be_using_on_every/
    logger.setLevel(logging.WARN + 10*args.quiet - 10*args.verbose)

    if not os.path.exists(args.sampledir):
        logger.fatal("Non existing sample directory %s", args.sampledir)
        sys.exit(1)
    if os.path.exists(args.samplecfg):
        logger.fatal("Cowardly refusing to overwrite existing %s", args.samplecfg)
        sys.exit(1)

    sampledir_to_cfg(args.sampledir, args.samplecfg)


if __name__ == "__main__":
    main()
