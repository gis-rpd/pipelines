#!/usr/bin/env python3

import sys
import os

import yaml
yaml.Dumper.ignore_aliases = lambda *args: True


def main(yaml_files):
    samples = {}
    readunits = {}
    print("Reading {} files".format(len(yaml_files)))
    for y in yaml_files:
        with open(y) as fh:
            d = yaml.safe_load(fh)
            for k, v in d['samples'].items():
                if k not in samples:
                    samples[k] = v
                else:
                    samples[k].extend(v)
            for k, v in d['readunits'].items():
                assert k not in readunits
                readunits[k] = v

    # sg10k specific
    assert len(readunits) == 4608, (
        "Got {} readunits. Expected {}".format(len(readunits), 4608))
    assert len(samples) == 96, (
        "Got {} readunits. Expected {}".format(len(samples), 96))
    set(len(v) for k, v in samples.items()) == {48}


    for sample_name, ru_keys in samples.items():
        rus = {}
        for k in ru_keys:
            rus[k] = readunits[k]
        sample = {sample_name: ru_keys}
        y = sample_name + ".yaml"
        if os.path.exists(y):
            sys.stderr.write("Refusing to overwrite existing {}\n".format(y))
            continue
        with open(y, 'w') as fh:
            yaml.dump(dict(samples=sample), fh, default_flow_style=False)
            yaml.dump(dict(readunits=rus), fh, default_flow_style=False)


if __name__ == "__main__":
    yaml_files = sys.argv[1:]
    main(yaml_files)
