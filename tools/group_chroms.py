#!/usr/bin/env python3

# will group chromosomes into consecutive groups, each not exceeding the length of the biggest chrom overall

#
from collections import OrderedDict
import copy
import sys

__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2017 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


def main(fai):
    chrom_lens = OrderedDict()
    with open(fai) as fh:
        for line in fh:
            chrom, size, _, _, _ = line.rstrip().split()
            size = int(size)
            assert chrom not in chrom_lens
            chrom_lens[chrom] = size
    chrom_lens_backup = copy.deepcopy(chrom_lens)
    maxlen = max(chrom_lens.values())
    
    num_printed = 0
    num_groups = 0
    while chrom_lens:
        buffered = OrderedDict()
        for c, l in chrom_lens.items():
            if sum(buffered.values()) + l <= maxlen:
                buffered[c] = l
            else:
                break
        #for c, l in buffered.items():
        #    print(c, l)
        #    num_printed += 1
        num_printed += len(buffered)
        num_groups += 1
        #print("group {}: {}".format(num_groups, list(buffered.items())))
        print("- [", end="")
        first = True
        print(", ".join(["'{}:{}-{}'".format(c, 1, l) for c, l in buffered.items()]), end="")
        print("]")
        
        for c in buffered:
            del chrom_lens[c]
    assert num_printed == len(chrom_lens_backup)


if __name__ == "__main__":
    assert len(sys.argv)==2, ("Need fai as input")
    fai = sys.argv[1]
    main(fai)
    sys.stderr.write("WARNING: this only makes sense if the fa file is roughly ordered by size (hg19 for example has chrM first)\n")
