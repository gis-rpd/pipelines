"""library functions for read units

following
http://gatkforums.broadinstitute.org/gatk/discussion/6472/read-groups
"""


#--- standard library imports
#
import logging
from collections import namedtuple
from itertools import zip_longest
import hashlib
import os

#--- third-party imports
#
import yaml

#--- project specific imports
#/


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


ReadUnit = namedtuple('ReadUnit', ['run_id', 'flowcell_id', 'library_id',
                                   'lane_id', 'rg_id', 'fq1', 'fq2'])


# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)


def gen_rg_lib_id(unit):
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


def fastqs_from_unit(unit):
    """FIXME:add-doc
    """
    if unit['fq2']:
        return unit['fq1'], unit['fq2']
    else:
        return unit['fq1']


def get_reads_unit_from_cfgfile(cfgfile):
    """Parse each ReadUnit in cfgfile and return as list"""
    read_units = []
    with open(cfgfile) as fh_cfg:
        for entry in yaml.safe_load(fh_cfg):
            if len(entry) == 6:
                rg_id = None
                [run_id, flowcell_id, library_id, lane_id, fq1, fq2] = entry
            elif len(entry) == 7:
                [run_id, flowcell_id, library_id, lane_id, fq1, fq2, rg_id] = entry
            else:
                logger.fatal("Couldn't parse read unit from '%s'", entry)
                raise ValueError(entry)

            # if we have relative paths, make them abs relative to cfgfile
            if fq1 and not os.path.isabs(fq1):
                fq1 = os.path.abspath(os.path.join(os.path.dirname(cfgfile), fq1))
            if fq2 and not os.path.isabs(fq2):
                fq2 = os.path.abspath(os.path.join(os.path.dirname(cfgfile), fq2))

            ru = ReadUnit._make([run_id, flowcell_id, library_id, lane_id,
                                 rg_id, fq1, fq2])
            if not rg_id or rg_id == 'None':
                ru = ru._replace(rg_id=create_rg_id_from_ru(ru))
            read_units.append(ru)
    return read_units


def get_reads_unit_from_args(fqs1, fqs2):
    """Turn fastq arguments into fake ReadUnits"""
    if fqs1:
        assert isinstance(fqs1, list)
    if fqs2:
        assert isinstance(fqs2, list)
        paired = True
    else:
        fqs2 = len(fqs1)*[None]
        paired = False

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
    read_units = []
    fq_pairs = list(zip_longest(fqs1, fqs2))
    for (fq1, fq2) in fq_pairs:
        run_id = flowcell_id = library_id = lane_id = rg_id = None
        fq1 = os.path.abspath(fq1)
        if fq2 is not None:
            fq2 = os.path.abspath(fq2)
        ru = ReadUnit._make(
            [run_id, flowcell_id, library_id, lane_id, rg_id, fq1, fq2])
        ru = ru._replace(rg_id=create_rg_id_from_ru(ru))
        read_units.append(ru)

    return read_units


def hash_for_fastq(fq1, fq2=None):
    """return hash for one or two fastq files based on filename only
    """
    m = hashlib.md5()
    m.update(fq1.encode())
    if fq2:
        m.update(fq2.encode())
    return m.hexdigest()[:8]


def key_for_read_unit(ru):
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
