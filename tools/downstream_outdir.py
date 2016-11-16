#!/usr/bin/env python3
"""Create downstream output folder string.

Just a hacky backport
"""

#--- standard library imports
#
import os
import sys
import argparse

#--- third-party imports
#
#/

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from pipelines import get_downstream_outdir
from pipelines import get_pipeline_version


__author__ = "Andreas WILM"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


def main():
    """main function
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-r', "--requestor", required=True,
                        help="Name of requestor (i.e. username)")
    parser.add_argument('-p', "--pipeline", required=True,
                        help="Pipeline name")
    args = parser.parse_args()
    pversion = get_pipeline_version().replace(" ", "-")
    print(get_downstream_outdir(args.requestor, args.pipeline,
                                pipeline_version=pversion))

    
if __name__ == "__main__":
    main()
