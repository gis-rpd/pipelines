"""Utility functions with no dependency outside the standard library
"""

#--- standard library imports
#
import os
from datetime import datetime

#--- third-party imports
#
#/ by design

#--- project specific imports
#
#/ by design


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"



def generate_timestamp():
    """generate ISO8601 timestamp incl microsends, but with colons
    replaced to avoid problems if used as file name
    """
    return datetime.isoformat(datetime.now()).replace(":", "-")


def timestamp_from_string(analysis_id):
    """
    converts output of generate_timestamp(), e.g. 2016-05-09T16-43-32.080740 back to timestamp
    """
    dt = datetime.strptime(analysis_id, '%Y-%m-%dT%H-%M-%S.%f')
    return dt



def parse_regions_from_bed(bed):
    """yields regions from bed as three tuple
    """

    with open(bed) as fh:
        for line in fh:
            if line.startswith('#') or not len(line.strip()) or line.startswith('track '):
                continue
            chrom, start, end = line.split()[:3]
            start, end = int(start), int(end)
            yield (chrom, start, end)


def chroms_and_lens_from_fasta(fasta):
    """return sequence and their length as two tuple. derived from fai
    """

    fai = fasta + ".fai"
    assert os.path.exists(fai), ("{} not indexed".format(fasta))
    with open(fai) as fh:
        for line in fh:
            (s, l) = line.split()[:2]
            l = int(l)
            yield (s, l)


def bed_and_fa_are_compat(bed, fasta):
    """checks whether samtools faidx'ed fasta is compatible with bed file
    """

    assert os.path.exists(bed), ("Missing file {}".format(bed))
    assert os.path.exists(fasta), ("Missing fasta index {}".format(fasta))

    bed_sqs = set([c for c, s, e in parse_regions_from_bed(bed)])
    fa_sqs = [c for c, l in chroms_and_lens_from_fasta(fasta)]

    return all([s in fa_sqs for s in bed_sqs])

