#!/usr/bin/env python3
"""Bundles and cleans the log directory of a pipeline run
"""

#--- standard library imports
#
import os
import sys

#--- third-party imports
#
# /

# --- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(os.path.join(os.path.dirname(
    os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from pipelines import bundle_and_clean_logs


__author__ = "Andreas WILM"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


def main():
    """main function"""

    assert len(sys.argv) == 2, ("Need pipeline outdir as only argument")
    pipeline_outdir = sys.argv[1]
    assert os.path.exists(pipeline_outdir)
    bundle_and_clean_logs(pipeline_outdir)


if __name__ == "__main__":
    main()
