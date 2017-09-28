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
import argparse

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



def check_expected_files(snakefile):
    """check expected files in snakefile dir"""

    is_ok = True
    pipeline_basedir = os.path.dirname(snakefile)
    pipeline_name = snakefile.split("/")[-2]
    expected_files = ['example-dag.pdf', 'README.md', 'Snakefile', 'tests.sh', 'cfg/modules.yaml', 'cfg/references.yaml']
    expected_files.extend(['cfg/cluster.{}.yaml'.format(site)
                           for site in ["GIS", "NSCC", "AWS"]])
    expected_files.append(pipeline_name + ".py")

    for f in expected_files:
        f = os.path.join(pipeline_basedir, f)
        if not os.path.exists(f):
            print("WARN: Missing file {}".format(f))
            is_ok = False
        
    return is_ok

    
def get_includes_from_snakefile(snakefile):
    includes = []
    with open(snakefile) as fh:
        for line in fh:
            if line.startswith("include: "):
                f = line.split()[1].replace(":", "").replace('"', "").replace("'", "")
                includes.append(os.path.relpath(
                    os.path.join(os.path.dirname(snakefile), f)))
    return includes

    
def check_benchmark_naming(snakefile):
    """check benchmark file naming"""
    is_ok = True
    seen_rules = dict()
    rules_with_benchmark = dict()

    with open(snakefile) as fh:
        rule = None
        for line in fh:
            if line.startswith("rule "):
                rulename = line.split()[1].replace(":", "")
                seen_rules[rulename] = 1
            if line.rstrip().endswith("benchmark:"):
                line = next(fh)
                while len(line.strip())==0 or line.strip().startswith("#"):
                    line = next(fh)
                benchmarkout = line.strip()
                benchmarkout = benchmarkout.replace("'", "").replace('"', "")
                rules_with_benchmark[rulename] = 1
                expsuf = '{}.benchmark.log'.format(rulename)
                if not benchmarkout.endswith(expsuf):
                    print("WARN: Mismatch in {} for rule {}: expected '{}' to end with '{}'".format(
                        snakefile, rulename, benchmarkout, expsuf))
                    is_ok = False
    rules_without_benchmark = set(seen_rules.keys()) - set(rules_with_benchmark.keys()) - set(["final"])
    if len(rules_without_benchmark) > 0:
        is_ok = False
        print("WARN: Rules without benchmark in {}: {}".format(
            snakefile, ', '.join(rules_without_benchmark)))
    return is_ok


def check_modules(pipeline_dir):
    """FIXME"""

    is_ok = True
    module_cfgs = glob.glob(os.path.join(pipeline_dir, "cfg/modules.yaml"))
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
            is_ok = False
        #else:
        #    print("OK: {}".format(cmd))
    return is_ok

        
def main(snakefiles, no_modules_check=False,
         no_benchmark_check=False):
    """main function"""

    logger.warning("include other existing tools here: check_cluster_conf.py, check_modules.py...")
    includes = []
    for f in snakefiles:
        assert os.path.exists(f)
        if not check_expected_files(f):
            print("Expected files FAILED: {}".format(f))
        else:
            print("Expected files OK: {}".format(f))
            
        if not no_modules_check:
            if not check_modules(f):
                print("Modules check FAILED: {}".format(f))
            else:
                print("Modules check OK: {}".format(f))
                
        includes.extend(get_includes_from_snakefile(f))

        
    for f in list(set(includes)) + snakefiles:
        if not no_benchmark_check:
            if not check_benchmark_naming(f):
                print("Benchmarking naming FAILED: {}".format(f))
            else:
                print("Benchmarking naming OK: {}".format(f))
                
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-M', "--no-modules-check", action="store_true",
                        help="Skip modules check")
    parser.add_argument('-B', "--no-benchmark-check", action="store_true",
                        help="Skip benchmark rule checks")
    parser.add_argument('snakefiles', nargs='*')
    args = parser.parse_args()
    
    main(args.snakefiles,
         no_modules_check=args.no_modules_check,
         no_benchmark_check=args.no_benchmark_check)