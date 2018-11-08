#!/usr/bin/env python3
"""Plotting of ViPR3 coverage and AF values
"""

#--- standard library imports
#
import os
import gzip
from collections import OrderedDict
import argparse

#--- third-party imports
#
import matplotlib
matplotlib.use("PDF")
import matplotlib.pyplot as plt
from matplotlib import rcParams
rcParams['xtick.direction'] = 'in'
rcParams['ytick.direction'] = 'in'

#--- project specific imports
#
# /


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2017 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


def parse_genomecov(genomecov_gzfile):
    """Parse gzipped bedtools genomecov output"""
    genomecov = OrderedDict()
    with gzip.open(genomecov_gzfile) as fh:
        for line in fh:
            sq, pos, cov = line.decode().rstrip().split("\t")
            pos = int(pos)-1
            cov = int(float(cov))# float for support of scientific notation
            if sq not in genomecov:
                genomecov[sq] = OrderedDict()
            genomecov[sq][pos] = cov
    return genomecov


def af_from_vcf(vcf_gz, snps_only=False):
    """Parse AF from INFO fields of LoFreq vcf's"""
    afs = OrderedDict()
    with gzip.open(vcf_gz) as fh:
        for line in fh:
            if line.decode().startswith("#"):
                continue
            sq, pos, _, ref, alt, _, _, info = line.decode().rstrip().split("\t")[:8]
            if snps_only:
                if len(ref) > 1 or len(alt) > 1:
                    continue
            pos = int(pos)-1
            af = [float(x[4:]) for x in info.split(";") if x.startswith("AF=")][0]
            if sq not in afs:
                afs[sq] = OrderedDict()
            # keep max af if multi-allelic
            af2 = afs[sq].get(pos)
            if af2 and af2 > af:
                af = af2
            afs[sq][pos] = af
    return afs


def parse_bed(fn):
    """Parses bed file fn and returns first three columns is iterator

    Adapted from LoFreq 2.1.2
    """
    with open(fn, 'r') as fh:
        for line in fh:            
            if line.startswith('#') or len(line.strip()) == 0:
                continue
            
            # bed should use tab as delimiter. use whitespace if tab fails.
            chrom = start = end = None
            for delim in ['\t', '']:
                ls = line.strip().split(delim)
                if len(ls) >= 3:
                    (chrom, start, end) = ls[0:3]
                    break
                if not chrom:
                    raise ValueError("Couldn't parse the following line"
                                     " from bed-file %s: %s" % (fn, line))
                
            # int(float()) allows for scientific notation
            (start, end) = [int(float(x)) for x in [start, end]]
            if end <= start or end < 0 or start < 0:
                raise ValueError("Invalid coordinates in the following line"
                                 " from bed-file %s: %s" % (fn, line))
            yield (chrom, start, end)

            
def plot(cov_gzfile, vcf_gzfile, plot_fn, bed_fn=None):
    """read cov and vcf and creates plot"""
    genomecov = parse_genomecov(cov_gzfile)
    afs = af_from_vcf(vcf_gzfile, snps_only=True)

    # only one genome allowed
    assert len(genomecov) == 1
    # only one sq is supported for plotting but could be 0 if vcf is empty
    assert len(afs) < 2
    sq = list(genomecov.keys())[0]

    if len(afs):
        assert sq in afs

    _, ax1 = plt.subplots()

    x1 = list(genomecov[sq].keys())
    y1 = list(genomecov[sq].values())

    if len(afs):
        x2 = list(afs[sq].keys())
        y2 = list(afs[sq].values())
    else:
        x2 = []
        y2 = []
        
    ylabel_size = 'medium'
    c = 'blue'
    lgd_cov = ax1.plot(x1, y1, color=c, label="Coverage")
    ax1.set_ylabel('Coverage', color=c, size=ylabel_size, weight='bold')
    #ax1.tick_params('y', color=c)
    ax1.set_yscale('log', basex=10)
    ax1.set_xlabel('Position', size='medium', weight='bold')

    ax1.set_ylim(bottom=1)# log!
    #ax1.grid(True, which='x')
    plt.gca().xaxis.grid(True)

    ax2 = ax1.twinx()

    lgd_gaps = None
    # plot bed on ax2 since non log scaled
    if bed_fn:
        gap_fill_coords = list(parse_bed(bed_fn))
        if len(gap_fill_coords):
            bed_sq = set([c[0] for c in gap_fill_coords])
            # ignoring chrom here. assuming 1 chrom only
            assert len(bed_sq)==1, ("Expected exactly one SQ in bed %s" % bed_fn)
            bed_sq = list(bed_sq)[0]
            assert bed_sq in afs, ("Bed SQ %s not found in AFs: %s" % (
                bed_sq, ', '.join(afs.keys())))

            c = 'green'
            #xmin = [c[1] for c in gap_fill_coords]
            #xmax = [c[2] for c in gap_fill_coords]
            #lgd_gaps = ax2.hlines([1]*len(xmin), xmin, xmax, colors=c,
            #                     linestyles='solid', lw=10, label='Gaps')
            for gfc in gap_fill_coords:
                xmin, xmax = gfc[1], gfc[2]
                lgd_gaps = ax2.axvspan(xmin, xmax, facecolor=c,
                                       alpha=0.3, label='Filled Gaps')
                # storing one is sufficient for legend
            
    c = 'red'
    lgd_vars = ax2.scatter(x2, y2, color=c, label="Variants")
    ax2.set_ylabel('Allele Freq.', color=c, size=ylabel_size, weight='bold')
    ax2.set_ylim(bottom=0, top=1)
    #ax2.tick_params('y', color=c)


    # weird hack to get the legend of two axis into one. See
    # https://stackoverflow.com/questions/5484922/secondary-axis-with-twinx-how-to-add-to-legend
    labs = []
    lobs = []
    for l in [lgd_cov, lgd_gaps, lgd_vars]:
        if l is None:
            continue
        try:
            lbl = l.get_label()
            lobs.append(l)
        except AttributeError:
            lbl = l[0].get_label()
            lobs.append(l[0])
        labs.append(lbl)        
    ax2.legend(lobs, labs, bbox_to_anchor=(1.1, 1), loc=2, borderaxespad=0.)

    plt.title(sq)
    plt.savefig(plot_fn, bbox_inches="tight")


def main():
    """main function"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-v", "--vcf", required=True,
                        help="LoFreq VCF files (gzipped)")
    parser.add_argument("-c", "--cov", required=True,
                        help="bedtools genomecov file (gzipped)")
    parser.add_argument("-p", "--plot", required=True,
                        help="Output plot filename (pdf format!).")
    parser.add_argument("-b", "--bed",
                        help="Bed file listing positions gap-filled with reference")
    args = parser.parse_args()

    assert not os.path.exists(args.plot)
    plot(args.cov, args.vcf, args.plot, bed_fn=args.bed)


if __name__ == "__main__":
    main()
