#!/usr/bin/env python3
"""
collection: gisds.runcomplete
"""


#--- standard library imports
#
from argparse import ArgumentParser
from os.path import abspath, dirname, join, realpath
from sys import path
import ldap

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = abspath(join(dirname(realpath(__file__)), "..", "lib"))
if LIB_PATH not in path:
    path.insert(0, LIB_PATH)
from mongodb import mongodb_conn
from pipelines import mux_to_lib


__author__ = "LIEW Jun Xian"
__email__ = "liewjx@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


def main():
    """
    Main function
    """
    instance = ArgumentParser(description=__doc__)
    instance.add_argument("-d", "--dir", help="specify one MUX_ID to generate OUT_DIR")
    instance.add_argument("-l", "--lib", help="specify one MUX_ID to generate LIB")
    args = instance.parse_args()

    if args.dir:
        for document in mongodb_conn(False).gisds.runcomplete.find({"analysis.per_mux_status.mux_id": args.dir}):
            if "analysis" in document:
                last_out_dir = ""
                for analysis in document["analysis"]:
                    if analysis["Status"].upper() != "FAILED":
                        if "per_mux_status" in analysis:
                            for mux in analysis["per_mux_status"]:
                                if mux["mux_id"] == args.dir:
                                    last_out_dir = analysis["out_dir"].replace("//", "/")
                print (last_out_dir)
    if args.lib:
        for lib in mux_to_lib(args.lib, testing=False):
            print (lib)

if __name__ == "__main__":
    main()
