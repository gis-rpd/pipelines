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

TARGETED_CFG=$RPD_ROOT/testing/data/illumina-platinum-NA12878/split1konly_pe.yaml
WES_FQ1=$RPD_ROOT/testing/data/illumina-platinum-NA12878/exome/SRR098401_1.fastq.gz
WES_FQ2=$RPD_ROOT/testing/data/illumina-platinum-NA12878/exome/SRR098401_2.fastq.gz
WGS_FQ1=$RPD_ROOT/testing/data/illumina-platinum-NA12878/ERR091571_1.fastq.gz
WGS_FQ2=$RPD_ROOT/testing/data/illumina-platinum-NA12878/ERR091571_2.fastq.gz
DUMMY_BED=$RPD_ROOT/testing/data/illumina-platinum-NA12878/human_g1k_v37_decoy_chr21.bed
TRUSEQ_BED=$RPD_ROOT/testing/data/illumina-platinum-NA12878/exome/truseq-exome-targeted-regions-manifest-v1-2.nochr.bed
DREAM_WGS_DIR=$RPD_ROOT/testing/data/somatic/icgc-tcga-dream-somatic/synthetic.challenge.set3/
INJ_BAM=$DREAM_WGS_DIR/normal.bam

rootdir=$(readlink -f $(dirname $0))
cd $rootdir
pipeline=$(pwd | sed -e 's,.*/,,')
commit=$(git describe --always --dirty)
test -e Snakefile || exit 1


log=$(mktemp)
COMPLETE_MSG="*** All tests completed ***"
echo "Logging to $log"
echo "Check log if the following final message is not printed: \"$COMPLETE_MSG\""


SKIP_REAL_TARGETED=0
SKIP_REAL_WES=0
SKIP_REAL_WGS=0


WRAPPER=./freebayes.py
targeted_cmd_base="$WRAPPER --sample-cfg $TARGETED_CFG -t targeted -l $DUMMY_BED --name 'test:targeted'";# --bam-only"
wes_cmd_base="$WRAPPER -1 $WES_FQ1 -2 $WES_FQ2 -s NA12878-WES -t WES -l $TRUSEQ_BED --name 'test:WES'";# --bam-only"
wes_run_cmd_base="../../run $(basename $WRAPPER .py) -1 $WES_FQ1 -2 $WES_FQ2 -s NA12878-WES -t WES -l $TRUSEQ_BED --name 'test:run:WES'"
wgs_cmd_base="$WRAPPER -1 $WGS_FQ1 -2 $WGS_FQ2 -s NA12878-WGS -t WGS --name 'test:WGS'"


# DAG
SKIP_DAG=1
if [ $SKIP_DAG -eq 0 ]; then
    echo "DAG: WES" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    eval $wes_cmd_base -o $odir -v --no-run >> $log 2>&1
    pushd $odir >> $log
    type=pdf;
    dag=example-dag.$type
    # FIXME simplify DAG by having only one cluster sed -i -e 's,num_chroms: .*,num_chroms: 1,' conf.yaml
    EXTRA_SNAKEMAKE_ARGS="--dag" bash run.sh; cat logs/snakemake.log | dot -T$type > $dag
    cp $dag $rootdir
    rm -rf $odir
    popd >> $log
fi


# dryruns
#
if [ $skip_dry_runs -ne 1 ]; then
    echo "Dryrun: targeted" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    # also testing --extra-conf
    eval $targeted_cmd_base -o $odir -v --extra-conf extrakey:extravalue --no-run >> $log 2>&1
    pushd $odir >> $log
    grep -q extrakey conf.yaml && echo "extra-conf works" >> $log 2>&1 || exit 1
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    popd >> $log
    rm -rf $odir
    
    echo "Dryrun: WES" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    eval $wes_cmd_base -o $odir -v --no-run >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    popd >> $log
    rm -rf $odir

    echo "Dryrun: WES bam only" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    eval $wes_cmd_base -o $odir --bam-only -v --no-run >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    popd >> $log
    rm -rf $odir

    echo "Dryrun: WES injected raw" | tee -a $log

    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    _wes_cmd_base="$WRAPPER -s NA12878-WES -t WES -l $TRUSEQ_BED --name 'test:WES'";# --bam-only"
    eval $_wes_cmd_base -o $odir --raw-bam $INJ_BAM -v --no-run >> $log 2>&1

    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    popd >> $log
    rm -rf $odir

    echo "Dryrun: WES injected post processed" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    eval $_wes_cmd_base -o $odir --proc-bam $INJ_BAM -v --no-run >> $log 2>&1

    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    popd >> $log
    rm -rf $odir

    # FIXME run wrapper should be tested somewhere else
    echo "Dryrun: WES through run wrapper" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    eval $wes_run_cmd_base -o $odir -v --no-run >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    popd >> $log
    rm -rf $odir

    echo "Dryrun: WGS" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    eval $wgs_cmd_base -o $odir -v --no-run >> $log 2>&1
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
    if [ $SKIP_REAL_TARGETED -eq 0 ]; then
        echo "Realrun: targeted" | tee -a $log
	odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
        eval $targeted_cmd_base -o $odir -v >> $log 2>&1
        # magically works even if line just contains id as in the case of pbspro
        jid=$(tail -n 1 $odir/logs/submission.log  | cut -f 3 -d ' ')
        echo "Started job $jid writing to $odir. You will receive an email"
    else
        echo "Skipping real targeted run due to config"
    fi
    
    if [ $SKIP_REAL_WES -eq 0 ]; then
        echo "Realrun: WES" | tee -a $log
	odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
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
	odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
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

