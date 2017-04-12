"""library functions for read units

following
http://gatkforums.broadinstitute.org/gatk/discussion/6472/read-groups
"""

# FIXME move read units into own class
# treated as pure dicts from within snakemake though


#--- standard library imports
#
import logging
from collections import namedtuple
from itertools import zip_longest
import hashlib
import os
import glob
import re

#--- third-party imports
#
import yaml

#--- project specific imports
#/


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


ReadUnit = namedtuple('ReadUnit',
                      ['run_id', 'flowcell_id', 'library_id', 'lane_id', 'rg_id', 'fq1', 'fq2'])


# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)


yaml.Dumper.ignore_aliases = lambda *args: True


def gen_rg_lib_id(unit):
    """generate read group lib id from readunit"""
    if unit['library_id']:
        return unit['library_id']
    else:
        return "LIB-DUMMY"


def get_sample_for_unit(unitname, config):
    """FIXME:add-doc
    """
    for samplename, readunits in config["samples"].items():
        if unitname in readunits:
            return samplename
    raise ValueError(unitname)


def gen_rg_pu_id(unit):
    """https://www.biostars.org/p/50349/"""
    if unit['run_id'] and unit['flowcell_id'] and unit['lane_id']:
        return "{}_{}.{}".format(unit['run_id'], unit['flowcell_id'], unit['lane_id'])
    else:
        return "PU-" + unit['rg_id']


# Taken from https://github.com/broadinstitute/viral-ngs/blob/master/pipes/rules/demux.rules
def objectify_remote(uri):
    if uri.lower().startswith('s3://'):
        import snakemake.remote.S3
        remote = snakemake.remote.S3.RemoteProvider()
        return remote.remote(uri[5:])
    elif uri.lower().startswith('gs://'):
        import snakemake.remote.GS
        remote = snakemake.remote.GS.RemoteProvider()
        return remote.remote(uri[5:])
    elif uri.lower().startswith('sftp://'):
        import snakemake.remote.SFTP
        remote = snakemake.remote.SFTP.RemoteProvider()
        return remote.remote(uri[7:])
    return uri


def fastqs_from_unit(unit):
    """FIXME is this really needed?
    """

    if unit['fq2']:
        return objectify_remote(unit['fq1']), objectify_remote(unit['fq2'])
    else:
        return objectify_remote(unit['fq1'])


def readunit_is_paired(unit):
    return unit['fq2'] is not None


def fastqs_from_unit_as_list(unit):
    """Return fastq files in unit as list, i.e. [fq1] if SE and [fq1, fq2]
    if PE
    """
    fqs = []
    fqs.append(unit['fq1'])
    if unit['fq2']:
        fqs.append(unit['fq2'])
    return [objectify_remote(x) for x in fqs]


def get_samples_and_readunits_from_cfgfile(cfgfile, raise_off=False):
    """Parse each ReadUnit in cfgfile and return as list
    """

    with open(cfgfile) as fh_cfg:
        yaml_data = yaml.safe_load(fh_cfg)
    unknown_keys = set(yaml_data.keys()) - set(['samples', 'readunits'])
    if unknown_keys:
        logger.critical("Found unexpected keys in %s (only 'samples'"
                        " and 'readunits' allowed): %s", cfgfile, unknown_keys)
        if not raise_off:
            raise ValueError(cfgfile)
    samples, readunits_plain = yaml_data['samples'], yaml_data['readunits']

    #logger.debug("samples: {}".format(samples))
    #logger.debug("readunits_plain keys: {}".format(readunits_plain.keys()))
    for sample_key, sample_rus in samples.items():
        for ru_key in sample_rus:
            if ru_key not in readunits_plain.keys():
                logger.critical("readunit %s of sample %s not found"
                                " in config file", ru_key, sample_key)
                if not raise_off:
                    raise ValueError(cfgfile)

    readunits = dict()# actual namedtuples instead of dict
    for ru_key, ru_plain in readunits_plain.items():
        for f in ['run_id', 'flowcell_id', 'library_id', 'lane_id']:
            if f not in ru_plain:
                logger.fatal("Missing field %s in config file %s", f, cfgfile)
                if not raise_off:
                    raise ValueError(cfgfile)
        run_id = ru_plain.get('run_id')
        flowcell_id = ru_plain.get('flowcell_id')
        library_id = ru_plain.get('library_id')
        lane_id = ru_plain.get('lane_id')
        rg_id = ru_plain.get('rg_id')# allowed to be none or missing
        fq1 = ru_plain.get('fq1')
        fq2 = ru_plain.get('fq2')

        # if we have s3 paths, leave them as they are, but make
        # relative paths abs relative to cfgfile
        if not os.path.isabs(fq1) and not fq1.startswith("s3://"):
            fq1 = os.path.abspath(os.path.join(os.path.dirname(cfgfile), fq1))
        if fq2 and not os.path.isabs(fq2) and not fq2.startswith("s3://"):
            fq2 = os.path.abspath(os.path.join(os.path.dirname(cfgfile), fq2))

        for f in [fq1, fq2]:
            if f and not os.path.exists(f) and not f.startswith("s3://"):
                logger.fatal("Non-existing input file %s in config file %s", f, cfgfile)
                if not raise_off:
                    raise ValueError(cfgfile)

        ru = ReadUnit(run_id, flowcell_id, library_id, lane_id, rg_id,
                      fq1, fq2)
        if not rg_id:
            ru = ru._replace(rg_id=create_rg_id_from_ru(ru))
        readunits[ru_key] = dict(ru._asdict())

    return samples, readunits


def get_readunits_from_args(fqs1, fqs2):
    """Turn fastq arguments into fake ReadUnits
    """

    if fqs1:
        assert isinstance(fqs1, list)

    if fqs2:
        assert isinstance(fqs2, list)
        paired = True
    else:
        fqs2 = len(fqs1)*[None]
        paired = False

    for f in fqs1 + fqs2:
        if f and not os.path.exists(f):
            logger.fatal("Non-existing input file %s", f)
            raise ValueError(f)

    if paired:
        print_fq_sort_warning = False
        # sorting here should ensure R1 and R2 match
        fq_pairs = list(zip_longest(sorted(fqs1), sorted(fqs2)))
        fq_pairs_orig = set(zip_longest(fqs1, fqs2))
        for (fq1, fq2) in fq_pairs:
            if (fq1, fq2) not in fq_pairs_orig:
                print_fq_sort_warning = True
                break
        if print_fq_sort_warning:
            logger.warning("Are you sure paired-end reads are in correct order?")

    if len(fqs1) != len(set(fqs1)):
        logger.warning("Looks like the same files was given twice?")
        #logger.debug("len(fqs1)={} len(set(fqs1))={}".format(len(fqs1), len(set(fqs1))))
    if paired:
        if len(fqs2) != len(set(fqs2)):
            logger.warning("Looks like the same files was given twice?")
            #logger.debug("len(fqs2)={} len(set(fqs2))={}".format(len(fqs2), len(set(fqs2))))

    readunits = dict()
    fq_pairs = list(zip_longest(fqs1, fqs2))
    for (fq1, fq2) in fq_pairs:
        run_id = flowcell_id = library_id = lane_id = rg_id = None
        fq1 = os.path.abspath(fq1)
        if fq2 is not None:
            fq2 = os.path.abspath(fq2)
        ru = ReadUnit(run_id, flowcell_id, library_id, lane_id, rg_id,
                      fq1, fq2)
        ru = ru._replace(rg_id=create_rg_id_from_ru(ru))
        readunits[key_for_readunit(ru)] = dict(ru._asdict())

    return readunits


def hash_for_fastq(fq1, fq2=None):
    """return hash for one or two fastq files based on filename only
    """
    m = hashlib.md5()
    m.update(fq1.encode())
    if fq2:
        m.update(fq2.encode())
    return m.hexdigest()[:8]


def key_for_readunit(ru):
    """used for file nameing hence made unique based on fastq file names
    """
    return hash_for_fastq(ru.fq1, ru.fq2)


def create_rg_id_from_ru(ru):
    """Same RG for files coming from same source. If no source info is
    given use fastq files names
    """
    if all([ru.run_id, ru.library_id, ru.lane_id]):
        return "{}.{}".format(ru.run_id, ru.lane_id)
    elif ru.fq1:
        # no source info? then use fastq file names
        return hash_for_fastq(ru.fq1, ru.fq2)


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
    schemes['bcl2fastq-2.17'] = re.compile(# FIXME untested. only for temp sg10k upload
        r'(?P<library_id>[A-Za-z0-9-]+)-(?P<barcode>[A-Za-z0-9-]+)_(?P<stuff>[A-Za-z0-9-]+)_L0*(?P<lane_id>[0-9-]+)_R(?P<read_no>[12])_(?P<part>[A-Za-z0-9-]+).fastq.gz')
    # WHH3550-CGCAACTA_S3_L002_R2_001.fastq.gz
    
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
    fq1s = glob.glob(os.path.join(sampledir, "*_R1*.fastq.gz"))
    assert len(fq1s), ("No files with matching names found")
    scheme = scheme_for_fastq(fq1s[0])
    readunits = dict()
    for fq1 in fq1s:
        match = scheme.search(os.path.basename(fq1))
        mgroups = match.groupdict()
        assert fq1.count("_R1") == 1, ("More than one occurence of _R1 in {}".format(fq1))
        fq2 = fq1.replace("_R1", "_R2")
        
        if not os.path.exists(fq2):
            fq2 = None
        rg = None
        
        ru = ReadUnit(mgroups.get('run_id'),
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
