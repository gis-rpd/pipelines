#!/usr/bin/env python3
"""Combine several samples config yamls into one
"""

#--- standard library imports
#
import sys
from itertools import chain

#--- third-party imports
#
import yaml

# --- project specific imports
#


yaml.Dumper.ignore_aliases = lambda *args: True


def main(yaml_files):
    """main function"""

    assert yaml_files, ("Need yummy yaml num nums")
    
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
                assert k not in readunits
                readunits[k] = v

    #with open(y, 'w') as fh:
    ru_used_idx = -1#pylint
    for ru_used_idx, ru_used in enumerate(chain.from_iterable([v for k, v in samples.items()])):
        assert ru_used in readunits
    assert ru_used_idx+1 == len(readunits), ("Mismatch between defined and used readgroups")

    with sys.stdout as fh:
        yaml.dump(dict(samples=samples), fh, default_flow_style=False)
        yaml.dump(dict(readunits=readunits), fh, default_flow_style=False)

        
if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.stderr.write("FATAL: Need path to yaml files as input\n")
        sys.exit(1)

    yaml_files = sys.argv[1:]
    main(yaml_files)
    sys.stderr.write("WARNING: fastq paths unchanged (only a problem if they are relative to input yaml and output yaml is somewhere else\n")
