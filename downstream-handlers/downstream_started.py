#!/usr/bin/env python3
"""FIXME
"""

#--- standard library imports
#
import logging
import sys
import os
import argparse

#--- third party imports
#
#/

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from starterflag import StarterFlag


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2017 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# global logger
LOGGER = logging.getLogger(__name__)
HANDLER = logging.StreamHandler()
HANDLER.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
LOGGER.addHandler(HANDLER)




def main():
    """main function
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-o', '--outdir', required=True,
                        help="Where to create start flag")
    parser.add_argument('-d', '--dbid', required=True,
                        help="Database id for started job")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Increase verbosity")
    parser.add_argument('-q', '--quiet', action='count', default=0,
                        help="Decrease verbosity")
    args = parser.parse_args()

    # Repeateable -v and -q for setting logging level.
    # See https://www.reddit.com/r/Python/comments/3nctlm/what_python_tools_should_i_be_using_on_every
    LOGGER.setLevel(logging.WARN + 10*args.quiet - 10*args.verbose)

    sflag = StarterFlag()
    sflag.write(args.outdir, args.dbid)
    LOGGER.info("Created %s", sflag.filename)



if __name__ == "__main__":
    main()
