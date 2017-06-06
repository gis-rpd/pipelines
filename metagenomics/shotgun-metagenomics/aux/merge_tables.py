#!/usr/bin/env python

"""
This file merges a few tables into one according to the first column.
It will be helpful in dealing with species abundance tables (metaphlan outputs).
"""

import os
import sys
import argparse
import re


import pandas as pd


def main(arguments):
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument('infiles', metavar='tabfile', nargs='+',
                        help='The dataframes to be merged.')

    parser.add_argument("-d", "--delimiter",
                        dest="sep",
                        default="\t",
                        help='The field delimiter. Default: [tab]')
    # FIXME: add multiple delimiter support?

    parser.add_argument("-p", "--pattern",
                        dest="pRegex",
                        help="Use part of the file names as the output column names. Default: [file base name]")

    parser.add_argument("-f", "--naFill",
                        dest="naFill",
                        type=float,
                        default=0.0,
                        help="Fill the missing values. Default: [0.0]")

    parser.add_argument("--header",
                        action="store_true",
                        dest="head_flag",
                        help="The files contain headers. Default: False (No header)")

    parser.add_argument('-o', '--outfile',
                        help="Output file. Default: stdout",
                        dest='outfile',
                        default=sys.stdout,
                        type=argparse.FileType('w'))

    args = parser.parse_args(arguments)

    ####################assign col names ####################
    filelist = []
    for f in args.infiles:
        ## remove empty files
        if os.stat(f).st_size > 0:
            filelist.append(f)


    filenames = [i.split('/')[-1] for i in filelist]

    if args.pRegex:
        regex = re.compile(args.pRegex)
        colnames = [regex.search(i).group() for i in filenames]
    else:
        colnames = filenames


    ####################merge data frames####################
    dfs = []
    for f in filelist:
        dfs.append(pd.read_table(f, sep=args.sep,
                                 skiprows=(1 if args.head_flag else None),
                                 header=None,
                                 index_col=0))

    # reduce renamed to functools.reduce but use discouraged
    df_merged = reduce(lambda left, right:
                       pd.merge(left, right, how='outer', left_index=True, right_index=True),
                       dfs).fillna(args.naFill)
    df_merged.columns = colnames
  #  print df_merged

    df_merged.to_csv(args.outfile, sep='\t', index_label='Index')

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
