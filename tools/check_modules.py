#!/usr/bin/env python3
"""Write a sample config for a given directory containing fastq files
following SRA naming conventions
"""

#--- standard library imports
#
import os
import sys
import logging
import glob
import subprocess

#--- third-party imports
#
import yaml

# --- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(os.path.join(os.path.dirname(
    os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from pipelines import get_init_call


__author__ = "Andreas WILM"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2017 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)


def main():
    """main function"""
    module_cfgs = glob.glob(os.path.join(LIB_PATH, "../*/*/cfg/modules.yaml"))
    modules = dict()
    for cfg in module_cfgs:
        with open(cfg) as fh:
            d = yaml.safe_load(fh)
        for p, v in d.items():
            modules[p] = v

    for p, v in modules.items():
        m = "{}/{}".format(p, v)
        cmd = ' '.join(get_init_call())
        cmd += "; module load {}".format(m)
        try:
            _ = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            sys.stderr.write("FAILED: {}\n".format(cmd))
        else:
            print("OK: {}".format(cmd))
if __name__ == "__main__":
    main()
