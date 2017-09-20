#!/usr/bin/env python3
"""Mirror a RPD snakemake setup, by creating symlinks to the results and copy of all scripts.
This allows to fork an existing analysis, reusing those results
"""

#--- standard library imports
#
import sys
import os
import shutil

#--- third-party imports
#/

#--- project specific imports
#/


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2017 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"



def snakemake_symlink_mirror(source_dir, target_dir):
    assert os.path.exists(os.path.join(source_dir, "out"))
        
    # symlink everything under "out"
    for root, dirs, files in os.walk(os.path.join(source_dir, "out")):
        for f in files:
            fabs = os.path.abspath(os.path.join(root, f))
            subpath = os.path.relpath(fabs, source_dir)
            t = os.path.join(target_dir, subpath)
            s = os.path.relpath(fabs, os.path.dirname(t))
            if not os.path.exists(os.path.dirname(t)):
                os.makedirs(os.path.dirname(t))
            os.symlink(s, t)
    
    # create empty logs dir
    os.mkdir(os.path.join(target_dir, "logs"))
    # copy rc dir
    shutil.copytree(os.path.join(source_dir, "rc"),
                    os.path.join(target_dir, "rc"))
    for f in ["run.sh", "conf.yaml", "cluster.yaml"]:
        shutil.copy(os.path.join(source_dir, f),
                    os.path.join(target_dir, f))
        
    

def main():
    assert len(sys.argv) == 3, ("Need source and target directory as input")
    source_dir = sys.argv[1]
    target_dir = sys.argv[2]

    print("Mirroring source_dir in target_dir")

    snakemake_symlink_mirror(source_dir, target_dir)
    
    print('Now try a dry-run:')
    print('  pushd {} && EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh; popd'.format(target_dir))
    print('If snakemake attempts a rerun (which it shouldn\'t), touch the symlinks:')
    print('  pushd {} && EXTRA_SNAKEMAKE_ARGS="--touch" bash run.sh; popd'.format(target_dir))

    
if __name__ == "__main__":
    main()
