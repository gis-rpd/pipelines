#!/usr/bin/env python3
"""Checks whether cluster config and Snakefile + rules match

"""

#--- standard library imports
#
import os
import logging
import argparse


#--- third-party imports
#
import yaml

#--- project specific imports
#
#/

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

def rules_and_includes_from_snakefile(snakefile):
    """not sure how to parse snakefile and all includes using API without
    config, so using poor mans version"""
    rules = []
    includes = []
    with open(snakefile) as fh:
        for line in fh:
            ls = line.strip()
            if len(ls) == 0:
                continue
            if ls.startswith("include:"):
                i = ls.replace("include:", "").strip(" \"'")
                includes.append(i)
            elif ls.startswith("rule "):
                r = ls.replace("rule ", "").strip(" \"':")
                rules.append(r)
    return rules, includes


def main():
    """main function
    """

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument('-s', "--snakefile", required=True,
                        help="Input snakefile")
    parser.add_argument('-c', "--clustercfg", required=True,
                        help="Input cluster config")
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

    with open(args.clustercfg) as fh:
        clustercfg = yaml.safe_load(fh)
    configured_rules = list(clustercfg.keys())

    used_rules = []
    snakefiles = [args.snakefile]
    while snakefiles:
        sf = snakefiles.pop()
        _rules, _includes = rules_and_includes_from_snakefile(sf)
        for i in _includes:
            if os.path.realpath(i):
                i = os.path.join(os.path.dirname(args.snakefile), i)
                snakefiles.append(i)
        used_rules.extend(_rules)

    extra = set(configured_rules) - set(used_rules) - set(['__default__'])
    if len(extra):
        print("Configured but unused rules: %s" % ' '.join(extra))

    defaults = set(used_rules) - set(configured_rules)
    if len(defaults):
        print("Rules defaulting to __default__: %s" % ' '.join(defaults))

if __name__ == "__main__":
    main()
