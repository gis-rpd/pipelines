#!/bin/bash

# FIXME reimplement in python

# http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euo pipefail

MYNAME=$(basename $(readlink -f $0))
#PIPELINE=$(basename $(dirname $MYNAME))
PIPELINE=$(basename $(dirname $(readlink -f $0)))
DOWNSTREAM_OUTDIR_PY=$(readlink -f $(dirname $MYNAME)/../../tools/downstream_outdir.py)

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

FQDIR=$RPD_ROOT/testing/data/vipr3/DENV2-TSV01-PDH203/
FQ1=$FQDIR/PDH203_GTGGCC_NA_R1.fastq.gz
FQ2=$FQDIR/PDH203_GTGGCC_NA_R2.fastq.gz
for f in $FQ1 $FQ2; do test -e$FQ1 || exit 1; done
# we have the actual ref which 94% similar to refseq used here
REF=$RPD_ROOT/testing/data/vipr3/ref/DENV_2.fa

rootdir=$(readlink -f $(dirname $0))
cd $rootdir
pipeline=$(pwd | sed -e 's,.*/,,')
commit=$(git describe --always --dirty)
test -e Snakefile || exit 1


log=$(mktemp)
COMPLETE_MSG="*** All tests completed ***"
echo "Logging to $log"
echo "Check log if the following final message is not printed: \"$COMPLETE_MSG\""


WRAPPER=./vipr.py
base_cmd="$WRAPPER -1 $FQ1 -2 $FQ2 -s test:DENV2-TSV01-PDH203 -r $REF";
# FIXME fix here and elsewhere

# DAG
SKIP_DAG=1
if [ $SKIP_DAG -eq 0 ]; then
    echo "Creating DAG" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    eval $base_cmd -o $odir -v --no-run >> $log 2>&1
    pushd $odir >> $log
    type=pdf;
    dag=example-dag.$type
    EXTRA_SNAKEMAKE_ARGS="--dag" bash run.sh; cat logs/snakemake.log | dot -T$type > $dag
    cp $dag $rootdir
    rm -rf $odir
    popd >> $log
fi


# dryruns
#
if [ $skip_dry_runs -ne 1 ]; then
    echo "Dryrun" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    # also testing --extra-conf
    eval $base_cmd -o $odir -v >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    popd >> $log
    rm -rf $odir
else
    echo "Dryrun tests skipped"
fi


# real runs
#
if [ $skip_real_runs -ne 1 ]; then
    echo "Realrun" | tee -a $log
	odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    eval $base_cmd -o $odir -v >> $log 2>&1
    # magically works even if line just contains id as in the case of pbspro
    jid=$(tail -n 1 $odir/logs/submission.log  | cut -f 3 -d ' ')
    echo "Started $jid writing to $odir. You will receive an email"
else
    echo "Real-run test skipped"
fi


echo
echo "$COMPLETE_MSG"

