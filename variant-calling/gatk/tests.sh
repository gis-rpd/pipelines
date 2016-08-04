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

TARGETED_CFG=$RPD_ROOT/testing/data/illumina-platinum-NA12878/split1konly_pe.yaml
WES_FQ1=$RPD_ROOT/testing/data/illumina-platinum-NA12878/exome/SRR098401_1.fastq.gz
WES_FQ2=$RPD_ROOT/testing/data/illumina-platinum-NA12878/exome/SRR098401_2.fastq.gz
WGS_FQ1=$RPD_ROOT/testing/data/illumina-platinum-NA12878/ERR091571_1.fastq.gz
WGS_FQ2=$RPD_ROOT/testing/data/illumina-platinum-NA12878/ERR091571_2.fastq.gz
DUMMY_BED=$RPD_ROOT/testing/data/illumina-platinum-NA12878/human_g1k_v37_decoy_chr21.bed
TRUSEQ_BED=$RPD_ROOT/testing/data/illumina-platinum-NA12878/exome/truseq-exome-targeted-regions-manifest-v1-2.nochr.bed
cd $(dirname $0)
pipeline=$(pwd | sed -e 's,.*/,,')
commit=$(git describe --always --dirty)
test -e Snakefile || exit 1


test_outdir_base=$RPD_ROOT/testing/output/${pipeline}/${pipeline}-commit-${commit}
log=$(mktemp)
COMPLETE_MSG="*** All tests completed ***"
echo "Logging to $log"
echo "Check log if the following final message is not printed: \"$COMPLETE_MSG\""


SKIP_REAL_WES=0
SKIP_REAL_WGS=1


WRAPPER=./gatk.py
targeted_cmd_base="$WRAPPER -c $TARGETED_CFG -s NA12878-targeted -t targeted -l $DUMMY_BED"
wes_cmd_base="$WRAPPER -1 $WES_FQ1 -2 $WES_FQ2 -s NA12878-WES -t WES -l $TRUSEQ_BED"
wgs_cmd_base="$WRAPPER -1 $WGS_FQ1 -2 $WGS_FQ2 -s NA12878-WGS -t WGS"

# dryruns
#
if [ $skip_dry_runs -ne 1 ]; then
    echo "Dryrun: targeted" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}-targeted.XXXXXXXXXX) && rmdir $odir
    eval $targeted_cmd_base -o $odir -v --no-run >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    rm -rf $odir
    popd >> $log
    
    echo "Dryrun: WES" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}-wes.XXXXXXXXXX) && rmdir $odir
    eval $wes_cmd_base -o $odir -v --no-run >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    rm -rf $odir
    popd >> $log

    echo "Dryrun: WGS" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}-wgs.XXXXXXXXXX) && rmdir $odir
    eval $wgs_cmd_base -o $odir -v --no-run >> $log 2>&1
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
    echo "Realrun: targeted" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}-targeted.XXXXXXXXXX) && rmdir $odir
    eval $targeted_cmd_base -o $odir -v >> $log 2>&1
    # magically works even if line just contains id as in the case of pbspro
    jid=$(tail -n 1 $odir/logs/submission.log  | cut -f 3 -d ' ')
    echo "Started job $jid writing to $odir. You will receive an email"
    
    if [ $SKIP_REAL_WES -eq 0 ]; then
        echo "Realrun: WES" | tee -a $log
        odir=$(mktemp -d ${test_outdir_base}-wes.XXXXXXXXXX) && rmdir $odir
        eval $wes_cmd_base -o $odir -v >> $log 2>&1
        # magically works even if line just contains id as in the case of pbspro
        jid=$(tail -n 1 $odir/logs/submission.log  | cut -f 3 -d ' ')
        echo "Started $jid writing to $odir. You will receive an email"
        #echo "DEBUG skipping WGS"; exit 1
    else
        echo "Skipping real WES run due to config"
    fi

    if [ $SKIP_REAL_WGS -eq 0 ]; then
        echo "Realrun: WGS" | tee -a $log
        odir=$(mktemp -d ${test_outdir_base}-wgs.XXXXXXXXXX) && rmdir $odir
        eval $wgs_cmd_base -o $odir -v >> $log 2>&1
        # magically works even if line just contains id as in the case of pbspro
        jid=$(tail -n 1 $odir/logs/submission.log  | cut -f 3 -d ' ')
        echo "Started $jid writing to $odir. You will receive an email"
    else
        echo "Skipping real WGS run due to config"
    fi
else
    echo "Real-run test skipped"
fi


echo
echo "$COMPLETE_MSG"

