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


def plot(cov_gzfile, vcf_gzfile, plot_file):
    """read cov and vcf and creates plot"""
    genomecov = parse_genomecov(cov_gzfile)
    afs = af_from_vcf(vcf_gzfile, snps_only=True)

    # only one genome allowed
    assert len(genomecov) == 1
    assert len(afs) == 1
    sq = list(genomecov.keys())[0]
    assert sq in afs

    _, ax1 = plt.subplots()

    x1 = list(genomecov[sq].keys())
    y1 = list(genomecov[sq].values())

    x2 = list(afs[sq].keys())
    y2 = list(afs[sq].values())

    ylabel_size = 'medium'
    c = 'blue'
    ax1.plot(x1, y1, color=c)
    ax1.set_ylabel('Coverage', color=c, size=ylabel_size, weight='bold')
    #ax1.tick_params('y', color=c)
    ax1.set_yscale('log', basex=10)
    ax1.set_xlabel('Position', size='medium', weight='bold')

    ax1.set_ylim(bottom=1)# log!
    #ax1.grid(True, which='x')
    plt.gca().xaxis.grid(True)

    c = 'red'
    ax2 = ax1.twinx()
    ax2.scatter(x2, y2, color=c)
    ax2.set_ylabel('SNP AF', color=c, size=ylabel_size, weight='bold')
    ax2.set_ylim(bottom=0, top=1)
    #ax2.tick_params('y', color=c)

    #fig.tight_layout()

    plt.title(sq)
    plt.savefig(plot_file)


def main():
    """main function"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-v", "--vcf", required=True,
                        help="LoFreq VCF files (gzipped)")
    parser.add_argument("-c", "--cov", required=True,
                        help="bedtools genomecov file (gzipped)")
    parser.add_argument("-p", "--plot", required=True,
                        help="Output plot filename (pdf format!).")
    args = parser.parse_args()

    assert not os.path.exists(args.plot)
    plot(args.cov, args.vcf, args.plot)


if __name__ == "__main__":
    main()
