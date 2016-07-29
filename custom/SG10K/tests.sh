#!/bin/bash

# FIXME reimplement in python

# http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euo pipefail

MYNAME=$(basename $(readlink -f $0))

toaddr() {
    if [ $(whoami) == 'userrig' ]; then
        echo "rpd@gis.a-star.edu.sg";
    else
        echo "$(whoami)@gis.a-star.edu.sg";
    fi
}

usage() {
    echo "$MYNAME: run pipeline tests"
    echo " -d: Run dry-run tests"
    echo " -r: Run real-run tests"
}
skip_dry_runs=1
skip_real_runs=1
while getopts "dr" opt; do
    case $opt in
        d)
            skip_dry_runs=0
            ;;
        r)
            skip_real_runs=0
            ;;
        \?)
            usage
            exit 1
            ;;
    esac
done


# readlink resolves links and makes path absolute
test -z "$RPD_ROOT" && exit 1
CFG=$RPD_ROOT/testing/data/SG10K/MUX3275-WHH474.one-per-run.yaml.tmp
SAMPLE=MUX3275-WHH474



cd $(dirname $0)
pipeline=$(pwd | sed -e 's,.*/,,')
commit=$(git describe --always --dirty)
test -e Snakefile || exit 1


test_outdir_base=$RPD_ROOT/testing/output/${pipeline}/${pipeline}-commit-${commit}
log=$(mktemp)
COMPLETE_MSG="*** All tests completed ***"
echo "Logging to $log"
echo "Check log if the following final message is not printed: \"$COMPLETE_MSG\""


# dryruns
#
if [ $skip_dry_runs -ne 1 ]; then
    echo "Dryrun: $SAMPLE" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}.XXXXXXXXXX) && rmdir $odir
    ./SG10K.py -c $CFG -o $odir --no-run >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    rm -rf $odir
    popd >> $log

else
    echo "Dryruns tests skipped"
fi


# real runs
#
if [ $skip_real_runs -ne 1 ]; then
    echo "Real run: $SAMPLE" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}.XXXXXXXXXX) && rmdir $odir
    ./SG10K.py -c $CFG -o $odir >> $log 2>&1
    echo "FIXME IMPLEMENT: test number of reads etc. as extra submitted job"
else
    echo "Real-run test skipped"
fi


echo
echo "$COMPLETE_MSG"
