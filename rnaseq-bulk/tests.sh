#!/bin/bash

# FIXME reimplement in python

# http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euo pipefail

MYNAME=$(basename $(readlink -f $0))

toaddr() {
    if [ $(whoami) == 'userrig' ]; then
        echo "rpd@mailman.gis.a-star.edu.sg";
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

FQDIR=$RPD_ROOT/testing/data/bulk-rnaseq/encode-data
R1_1M=$FQDIR/ENCFF001RDF_NA_NA_R1_001_1M.fastq.gz
R1_500K_1=$FQDIR/ENCFF001RDF_NA_NA_R1_001_500K-1.fastq.gz
R1_500K_2=$FQDIR/ENCFF001RDF_NA_NA_R1_001_500K-2.fastq.gz
R2_1M=$FQDIR/ENCFF001RCX_NA_NA_R2_001_1M.fastq.gz
R2_500K_1=$FQDIR/ENCFF001RCX_NA_NA_R2_001_500K-1.fastq.gz
R2_500K_2=$FQDIR/ENCFF001RCX_NA_NA_R2_001_500K-2.fastq.gz
SAMPLE=ENCFF001

cd $(dirname $0)
pipeline=$(pwd | sed -e 's,.*/,,')
commit=$(git describe --always --dirty)
test -e Snakefile || exit 1


test_outdir_base=$RPD_ROOT/testing/output/${pipeline}/${pipeline}-commit-${commit}
log=$(mktemp)
COMPLETE_MSG="*** All tests completed ***"
echo "Logging to $log"
echo "Check log if the following final message is not printed: \"$COMPLETE_MSG\""


WRAPPER=./rnaseq-bulk.py
# SE command resulting in 1M reads total
CMD_1_SE_1M="$WRAPPER -1 $R1_1M -s $SAMPLE"
CMD_2_SE_500K="$WRAPPER -1 $R1_500K_1 $R1_500K_2 -s $SAMPLE"
# PE command resulting in 2M reads total
CMD_1_PE_1M="$WRAPPER -1 $R1_1M -2 $R2_1M -s $SAMPLE"
CMD_2_PE_500K="$WRAPPER -1 $R1_500K_1 $R1_500K_2 -2 $R2_500K_1 $R2_500K_2 -s $SAMPLE"



# dryruns
#
if [ $skip_dry_runs -ne 1 ]; then
    echo "Dryrun: 2 500K SE fastqs" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}.XXXXXXXXXX) && rmdir $odir
    eval $CMD_2_SE_500K -o $odir -v --no-run >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    rm -rf $odir
    popd >> $log

    echo "Dryrun: 2 500K PE fastq pairs" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}.XXXXXXXXXX) && rmdir $odir
    eval $CMD_2_PE_500K -o $odir -v --no-run >> $log 2>&1
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
    echo "Dryrun: 1 1M SE fastq" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}.XXXXXXXXXX) && rmdir $odir
    eval $CMD_1_SE_1M -o $odir -v >> $log 2>&1
    # magically works even if line just contains id as in the case of pbspro
    jid=$(tail -n 1 $odir/logs/submission.log  | cut -f 3 -d ' ')
    echo "Started job $jid writing to $odir. You will receive an email"

    echo "Dryrun: 2 500K SE fastqs" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}.XXXXXXXXXX) && rmdir $odir
    eval $CMD_2_SE_500K -o $odir -v >> $log 2>&1
    # magically works even if line just contains id as in the case of pbspro
    jid=$(tail -n 1 $odir/logs/submission.log  | cut -f 3 -d ' ')
    echo "Started job $jid writing to $odir. You will receive an email"

    echo "Dryrun: 1 1M PE fastq pair" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}.XXXXXXXXXX) && rmdir $odir
    eval $CMD_1_PE_1M -o $odir -v >> $log 2>&1
    # magically works even if line just contains id as in the case of pbspro
    jid=$(tail -n 1 $odir/logs/submission.log  | cut -f 3 -d ' ')
    echo "Started job $jid writing to $odir. You will receive an email"    

    echo "Dryrun: 2 500K PE fastq pairs" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}.XXXXXXXXXX) && rmdir $odir
    eval $CMD_2_PE_500K -o $odir -v >> $log 2>&1
    # magically works even if line just contains id as in the case of pbspro
    jid=$(tail -n 1 $odir/logs/submission.log  | cut -f 3 -d ' ')
    echo "Started job $jid writing to $odir. You will receive an email"

    echo "FIXME check number of reads in output"
else
    echo "Real-run test skipped"
fi


echo
echo "$COMPLETE_MSG"

