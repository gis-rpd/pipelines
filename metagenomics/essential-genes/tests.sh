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
TEST_DATA_DIR=$RPD_ROOT/testing/data/essential-genes/
#REF=$TEST_DATA_DIR/NC_017550.1.fa
#REF=$RPD_GENOMES/essential-genes/Propionibacterium_acnes/NC_017550.1.fa
#GENOME=Propionibacterium_acnes_ATCC_11828_uid162177
FQ1=$TEST_DATA_DIR/WBE005_decont_human_1.fastq.gz
FQ2=$TEST_DATA_DIR/WBE005_decont_human_2.fastq.gz
SAMPLE=WBE005


for f in $FQ1 $FQ2; do
    if [ ! -e $f ]; then
        echo "FATAL: non existant file $f" 1>&2
        exit 1
    fi
done


rootdir=$(readlink -f $(dirname $0))
cd $rootdir
pipeline=$(pwd | sed -e 's,.*/,,')
commit=$(git describe --always --dirty)
test -e Snakefile || exit 1


test_outdir_base=$RPD_ROOT/testing/output/${pipeline}/${pipeline}-commit-${commit}
log=$(mktemp)
COMPLETE_MSG="*** All tests completed ***"
echo "Logging to $log"
echo "Check log if the following final message is not printed: \"$COMPLETE_MSG\""


# DAG
SKIP_DAG=1
if [ $SKIP_DAG -eq 0 ]; then
    echo "DAG" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}.XXXXXXXXXX) && rmdir $odir
    #./essential-genes.py -g $GENOME -r $REF -1 $FQ1 -2 $FQ2 -s WBE005 --no-run --no-mail -o $odir >> $log 2>&1
    ./essential-genes.py -1 $FQ1 -2 $FQ2 -s WBE005 --no-run --no-mail -o $odir >> $log 2>&1
    pushd $odir >> $log
    type=pdf
    dag=example-dag.$type
    EXTRA_SNAKEMAKE_ARGS="--dag" bash run.sh; cat logs/snakemake.log | dot -T$type > $dag
    cp $dag $rootdir
    popd >> $log
    rm -rf $odir
fi

# dryruns
#
if [ $skip_dry_runs -ne 1 ]; then
    echo "Dryrun" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}.XXXXXXXXXX) && rmdir $odir
    #./essential-genes.py -g $GENOME -r $REF -1 $FQ1 -2 $FQ2 -s WBE005 --no-run --no-mail -o $odir >> $log 2>&1
    ./essential-genes.py -1 $FQ1 -2 $FQ2 -s WBE005 --no-run --no-mail -o $odir >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    popd >> $log
    rm -rf $odir

else
    echo "Dryruns tests skipped"
fi


# real runs
#
if [ $skip_real_runs -ne 1 ]; then
    echo "Real run" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}.XXXXXXXXXX) && rmdir $odir
    #./essential-genes.py -g $GENOME -r $REF -1 $FQ1 -2 $FQ2 -s WBE005 -o $odir >> $log 2>&1
    ./essential-genes.py -1 $FQ1 -2 $FQ2 -s WBE005 -o $odir >> $log 2>&1
    
else
    echo "Real-run test skipped"
fi


echo
echo "$COMPLETE_MSG"
