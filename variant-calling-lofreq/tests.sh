#!/bin/bash

# FIXME reimplement in python

# http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euo pipefail

MYNAME=$(basename $(readlink -f $0))
KEEP_TMP=1

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
NA12878_DIR=$RPD_ROOT/testing/data/illumina-platinum-NA12878
#R1_1M=ERR091571_1_split000001_1M-only.fastq.gz
#R2_1M=ERR091571_2_split000001_1M-only.fastq.gz
R1_1K=$NA12878_DIR/ERR091571_1_split000001_1konly.fastq.gz
R2_1K=$NA12878_DIR/ERR091571_2_split000001_1konly.fastq.gz
SAMPLE_1K=NA12878-1K

for f in $R1_1K $R2_1K; do
    if [ ! -e $f ]; then
        echo "FATAL: non existant file $f" 1>&2
        exit 1
    fi
done


cd $(dirname $0)
pipeline=$(pwd | sed -e 's,.*/,,')
commit=$(git describe --always --dirty)
test -e Snakefile || exit 1


test_outdir_base=/mnt/projects/rpd/testing/output/${pipeline}/${pipeline}-commit-${commit}
log=$(mktemp)
COMPLETE_MSG="*** All tests completed ***"
echo "Logging to $log"
echo "Check log if the following final message is not printed: \"$COMPLETE_MSG\""


# dryruns
#
if [ $skip_dry_runs -ne 1 ]; then
    echo "Dryrun: $SAMPLE_1K" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}-dryrun-$SAMPLE_1K.XXXXXXXXXX) && rmdir $odir
    ./variant-calling-lofreq.py -1 $R1_1K -2 $R2_1K -s $SAMPLE_1K -d -o $odir --no-run >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    popd >> $log
    test $KEEP_TMP -eq  1 || rm -rf $odir
else
    echo "Dryruns tests skipped"
fi


# real runs
#
if [ $skip_real_runs -ne 1 ]; then
    echo "Real run: $SAMPLE_1K" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}-realrun-$SAMPLE_1K.XXXXXXXXXX) && rmdir $odir
    ./variant-calling-lofreq.py -1 $R1_1K -2 $R2_1K -s $SAMPLE_1K -d -o $odir >> $log 2>&1
    #pushd $odir >> $log
    #EXTRA_SNAKEMAKE_ARGS="--notemp" bash run.sh >> $log 2>&1
    #EXTRA_SNAKEMAKE_ARGS="--notemp" 
    #bash run.sh >> $log 2>&1
    #popd >> $log
    echo "Started job in $odir. You will receive an email"
    test $KEEP_TMP -eq  1 || rm -rf $odir       
else
    echo "Real-run test skipped"
fi


echo
echo "$COMPLETE_MSG"
