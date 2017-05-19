#!/bin/bash

# FIXME reimplement in python

# http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euo pipefail

MYNAME=$(basename $(readlink -f $0))
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


DATA_DIR=$RPD_ROOT/testing/data/chipseq/encode/HEK293eGFP-ZNF71/
CTRL_R1=$DATA_DIR/control/ENCFF557HNG.fastq.gz
CTRL_R2=$DATA_DIR/control/ENCFF453HUS.fastq.gz
REP1_R1=$DATA_DIR/eGFP-ZNF71/ENCFF244FZX.fastq.gz
REP1_R2=$DATA_DIR/eGFP-ZNF71/ENCFF413ZHB.fastq.gz
#REP2_R1=$DATA_DIR/eGFP-ZNF71/ENCFF369REJ.fastq.gz
#REP2_R2=$DATA_DIR/eGFP-ZNF71/ENCFF123UWV.fastq.gz


rootdir=$(readlink -f $(dirname $0))
cd $rootdir
pipeline=$(pwd | sed -e 's,.*/,,')
commit=$(git describe --always --dirty)
test -e Snakefile || exit 1

log=$(mktemp)
COMPLETE_MSG="*** All tests completed ***"
echo "Logging to $log"
echo "Check log if the following final message is not printed: \"$COMPLETE_MSG\""


#SKIP_REAL_TARGETED=0
WRAPPER=./chipseq.py


rep1_pe_basecmd="$WRAPPER --control-fq1 $CTRL_R1 --treatment-fq1 $REP1_R1"
rep1_se_basecmd="$WRAPPER --control-fq1 $CTRL_R1 --treatment-fq1 $REP1_R1"


echo 'FIXME test quality of results' 1>&2
echo 'FIXME bam injection' 1>&2


# DAG
SKIP_DAG=1
if [ $SKIP_DAG -eq 0 ]; then
    echo "DAG: WES" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    eval $rep1_pe_basecmd -t TF -o $odir -v --no-run >> $log 2>&1
    pushd $odir >> $log
    type=pdf;
    dag=example-dag.$type
    sed -i -e 's,num_chroms: .*,num_chroms: 1,' conf.yaml
    EXTRA_SNAKEMAKE_ARGS="--dag" bash run.sh; cat logs/snakemake.log | dot -T$type > $dag
    cp $dag $rootdir
    rm -rf $odir
    popd >> $log
fi



# dryruns
#
if [ $skip_dry_runs -ne 1 ]; then
    echo "Dryrun: TF PE" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    eval $rep1_pe_basecmd -t TF -o $odir -v --no-run >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    popd >> $log
    rm -rf $odir

    echo "Dryrun: TF SE" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    eval $rep1_se_basecmd -t TF -o $odir -v --no-run >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    popd >> $log
    rm -rf $odir
    
    echo "Dryrun: skip dfilter" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    eval $rep1_pe_basecmd -t TF --skip-dfilter -o $odir -v --no-run >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    popd >> $log
    rm -rf $odir

    echo "Dryrun: histone narrow" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    eval $rep1_pe_basecmd -t histone-narrow -o $odir -v --no-run >> $log 2>&1
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
    echo "Real Run: TF PE" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    eval $rep1_pe_basecmd -t TF -o $odir -v >> $log 2>&1
    # magically works even if line just contains id as in the case of pbspro
    jid=$(tail -n 1 $odir/logs/submission.log  | cut -f 3 -d ' ')
    echo "Started job $jid writing to $odir. You will receive an email"

    echo "Real Run: TF SE" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    eval $rep1_se_basecmd -t TF -o $odir -v >> $log 2>&1
    # magically works even if line just contains id as in the case of pbspro
    jid=$(tail -n 1 $odir/logs/submission.log  | cut -f 3 -d ' ')
    echo "Started job $jid writing to $odir. You will receive an email"
    
else
    echo "Real-run test skipped"
fi


echo
echo "$COMPLETE_MSG"

    


