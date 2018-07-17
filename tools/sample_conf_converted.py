#!/usr/bin/env python3
"""Convert pre 2018 samples yaml format to the new one which contains
readunits under samples
"""

#--- standard library imports
#
import sys
import os

#--- third-party imports
#
# /

# --- project specific imports
#
import yaml
yaml.Dumper.ignore_aliases = lambda *args: True



__author__ = "Andreas WILM"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2018 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"



def convert(in_fn, out_fn):
    
    with open(in_fn) as fh:
        old_data = yaml.load(fh)
    present_keys = list(old_data.keys())
    expected_keys = ['samples', 'readunits']
    assert sorted(present_keys) == sorted(expected_keys), (
        "Only expected %s but found %s data in %s" % (
            ', '.join(expected_keys), ', '.join(present_keys), in_fn))
    
    new_data = dict()
    for sk, rk_list in old_data['samples'].items():
        assert sk not in new_data
        new_data[sk] = {'readunits': dict()}
        for rk in rk_list:
            new_data[sk]['readunits'][rk] = old_data['readunits'][rk]

    yaml.dump(dict(samples=new_data), sys.stdout, default_flow_style=False)


def main():
    """main function
    """

    old_yaml_fn = sys.argv[1]
    new_yaml_fn = sys.argv[2]
    sys.stderr.write("Converting %s to %s\n" % (old_yaml_fn, new_yaml_fn))
    assert os.path.exists(old_yaml_fn)
    assert not os.path.exists(new_yaml_fn)
    convert(old_yaml_fn, new_yaml_fn)

    
if __name__ == "__main__":
    main()
