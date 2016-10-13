#!/usr/bin/env python3
"""Creates a config file describing your samples that can be used as
input for all pipelines (-c)

"""

#--- standard library imports
#
import sys
import os
import argparse
import logging
import csv

#--- third-party imports
#
import yaml

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from readunits import ReadUnit
from readunits import create_rg_id_from_ru
from readunits import key_for_readunit

__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# only dump() and following do not automatically create aliases
yaml.Dumper.ignore_aliases = lambda *args: True


# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)


def main():
    """main function
    """

    parser = argparse.ArgumentParser(description=__doc__)

    # generic args
    csv_cols = ['sample'] + list(ReadUnit._fields)
    parser.add_argument('-i', "--csv", required=True,
                        help="CSV input file describing your samples using the"
                        " following columns: {} (sample and fq1 are mandatory; leave unknown fields empty)".format(
                            ", ".join("{}:{}".format(i+1, c) for i, c in enumerate(csv_cols))))
    parser.add_argument('-o', "--yaml", required=True,
                        help="Output config (yaml) file")
    parser.add_argument('-d', '--delimiter', default="\t",
                        help="Use this delimiter for CSV (default is <tab>)")
    parser.add_argument('-f', '--force-overwrite', action='store_true',
                        help="Force overwriting of existing file")
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

    if len(args.delimiter) != 1:
        logger.fatal("Delimiter needs to be exactly one character")
        sys.exit(1)
    if not os.path.exists(args.csv):
        logger.fatal("Input file %s does not exist", args.csv)
        sys.exit(1)
    if os.path.exists(args.yaml) and not args.force_overwrite:
        logger.fatal("Cowardly refusing to overwrite existing file %s", args.yaml)
        sys.exit(1)

    samples = dict()
    readunits = dict()

    with open(args.csv) as csvfile:
        csvreader = csv.reader(csvfile, delimiter=args.delimiter)
        for row in csvreader:
            if len(row) == 0:
                continue
            logger.debug("DEBUG row %s", "\t".join("{}:{}".format(k, v) for k, v in zip(csv_cols, row)))
            if len(row) != len(csv_cols):
                logger.fatal("Only found %s fields (require %s) in row: %s", len(row), len(csv_cols), '\t'.join(row))
                sys.exit(1)
            sample_name = row[0]
            ru_fields = row[1:]
            ru_fields = [x if len(x.strip()) else None for x in ru_fields]
            #sys.stderr.write("ru_fields={}".format(ru_fields) + "\n")
            ru = ReadUnit._make(ru_fields)
            if not ru.rg_id:
                ru = ru._replace(rg_id=create_rg_id_from_ru(ru))
            ru_key = key_for_readunit(ru)

            readunits[ru_key] = dict(ru._asdict())
            if sample_name not in samples:
                samples[sample_name] = []
            samples[sample_name].append(ru_key)

    with open(args.yaml, 'w') as fh:
        yaml.dump(dict(samples=samples), fh, default_flow_style=False)
        yaml.dump(dict(readunits=readunits), fh, default_flow_style=False)

if __name__ == "__main__":
    main()
