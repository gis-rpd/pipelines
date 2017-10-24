#!/usr/bin/env python3
"""Combine several samples config yamls into one
"""

#--- standard library imports
#
import sys
from os.path import exists, isabs, abspath, dirname, join, relpath
from itertools import chain
import argparse

#--- third-party imports
#
import yaml

# --- project specific imports
#


yaml.Dumper.ignore_aliases = lambda *args: True


def main(yaml_files, yaml_out, use_abspath=False):
    """main function"""

    assert yaml_files, ("Need yummy yaml num nums")
    assert not exists(yaml_out)

    readunits = {}
    samples = {}
    #sys.stderr.write("Reading {} files".format(len(yaml_files)))
    for y in yaml_files:
        with open(y) as fh:
            d = yaml.safe_load(fh)
            assert sorted(d.keys()) == sorted(['samples', 'readunits'])
            for k, v in d['samples'].items():
                if k not in samples:
                    samples[k] = v
                else:
                    samples[k].extend(v)
            for k, v in d['readunits'].items():
                assert k not in readunits, ("Already got key {} for {} in readunits: {}".format(k, v, readunits))
                # fastq path might be relativ to its config. make
                # absolute first, otgerwise next operations won't work
                if not isabs(v['fq1']):
                    v['fq1'] = abspath(join(dirname(y), v['fq1']))
                    assert exists(v['fq1']), v['fq1']
                if 'fq2' in v and not isabs(v['fq2']):
                    v['fq2'] = abspath(join(dirname(y), v['fq2']))
                    assert exists(v['fq2']), v['fq2']

                if use_abspath:
                    v['fq1'] = abspath(v['fq1'])
                    if 'fq2' in v:
                        v['fq2'] = abspath(v['fq2'])
                elif yaml_out != "-":
                    v['fq1'] = relpath(abspath(v['fq1']), dirname(yaml_out))
                    if 'fq2' in v:
                        v['fq2'] = relpath(abspath(v['fq2']), dirname(yaml_out))


                readunits[k] = v
                #print("DEBUG", v['fq1'], v['fq2'])
    #with open(y, 'w') as fh:
    ru_used_idx = -1#pylint
    for ru_used_idx, ru_used in enumerate(chain.from_iterable([v for k, v in samples.items()])):
        assert ru_used in readunits
    assert ru_used_idx+1 == len(readunits), ("Mismatch between defined and used readgroups")

    if yaml_out == "-":
        fh = sys.stdout
    else:
        fh = open(yaml_out, 'w')
    yaml.dump(dict(samples=samples), fh, default_flow_style=False)
    yaml.dump(dict(readunits=readunits), fh, default_flow_style=False)
    if fh != sys.stdout:
        fh.close()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-y', "--cfgs", nargs="+", required=True,
                        help="sample configs to merge")
    parser.add_argument('-a', "--abs", action="store_true",
                        help="Make FastQ paths absolute (otherwise make relative to output)")
    default = "-"
    parser.add_argument('-o', "--out", default=default,
                        help="Output yaml file ('-' for stdout, default={})".format(default))
    args = parser.parse_args()
    main(args.cfgs, args.out, args.abs)
