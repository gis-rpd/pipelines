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

FQDIR=$RPD_ROOT/testing/data/rnaseq/encode-data
R1_1M=$FQDIR/ENCFF001RDF_NA_NA_R1_001_1M.fastq.gz
R1_500K_1=$FQDIR/ENCFF001RDF_NA_NA_R1_001_500K-1.fastq.gz
R1_500K_2=$FQDIR/ENCFF001RDF_NA_NA_R1_001_500K-2.fastq.gz
R2_1M=$FQDIR/ENCFF001RCX_NA_NA_R2_001_1M.fastq.gz
R2_500K_1=$FQDIR/ENCFF001RCX_NA_NA_R2_001_500K-1.fastq.gz
R2_500K_2=$FQDIR/ENCFF001RCX_NA_NA_R2_001_500K-2.fastq.gz
R1_FULL=$FQDIR/ENCFF001RDF_NA_NA_R1_001.fastq.gz
R2_FULL=$FQDIR/ENCFF001RCX_NA_NA_R2_001.fastq.gz
SAMPLE=ENCFF001

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
if [ $skip_real_runs -ne 1 ]; then
    echo "Also check log if the check against expected output hold jobs fail"
fi


WRAPPER=./star-rsem.py
# SE command resulting in 1M reads total
CMD_1_SE_1M="$WRAPPER -C -1 $R1_1M -s $SAMPLE --name 'test:1_SE_1M'"
CMD_2_SE_500K="$WRAPPER -C -1 $R1_500K_1 $R1_500K_2 -s $SAMPLE --name 'test:2_SE_500K'"
# PE command resulting in 2M reads total
CMD_1_PE_1M="$WRAPPER -C -1 $R1_1M -2 $R2_1M -s $SAMPLE --name 'test:1_PE_1M'"
CMD_2_PE_500K="$WRAPPER -C -1 $R1_500K_1 $R1_500K_2 -2 $R2_500K_1 $R2_500K_2 -s $SAMPLE --name 'test:2_PE_500K'"
CMD_FULL="$WRAPPER -1 $R1_FULL -2 $R2_FULL -s $SAMPLE --name 'test:FULL'"


SKIP_REAL_FULL=0

# DAG
SKIP_DAG=1
if [ $SKIP_DAG -eq 0 ]; then
    echo "DAG: Full" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}.XXXXXXXXXX) && rmdir $odir
    eval $CMD_FULL -o $odir -v --no-run >> $log 2>&1
    pushd $odir >> $log
    type=pdf;
    dag=example-dag.$type
    EXTRA_SNAKEMAKE_ARGS="--dag" bash run.sh; cat logs/snakemake.log | dot -T$type > $dag
    cp $dag $rootdir
    popd >> $log
    rm -rf $odir
fi

    
# dryruns
#
if [ $skip_dry_runs -ne 1 ]; then
    echo "Dryrun: 2 500K SE fastqs" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}.XXXXXXXXXX) && rmdir $odir
    eval $CMD_2_SE_500K -o $odir -v --no-run >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    popd >> $log
    rm -rf $odir

    echo "Dryrun: 2 500K PE fastq pairs" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}.XXXXXXXXXX) && rmdir $odir
    eval $CMD_2_PE_500K -o $odir -v --no-run >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    popd >> $log
    rm -rf $odir

    echo "Dryrun: Full" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}.XXXXXXXXXX) && rmdir $odir
    eval $CMD_FULL -o $odir -v --no-run >> $log 2>&1
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
    echo "Real run: 1 1M SE fastq" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}.XXXXXXXXXX) && rmdir $odir
    eval $CMD_1_SE_1M -o $odir -v >> $log 2>&1
    # magically works even if line just contains id as in the case of pbspro
    jid1=$(tail -n 1 $odir/logs/submission.log  | cut -f 3 -d ' ')
    echo "Started job $jid1 writing to $odir. You will receive an email"
    bam1=$odir/out/$SAMPLE/star/${SAMPLE}_hg19_Aligned.sortedByCoord.out.bam
    
    echo "Real run: 2 500K SE fastqs" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}.XXXXXXXXXX) && rmdir $odir
    eval $CMD_2_SE_500K -o $odir -v >> $log 2>&1
    # magically works even if line just contains id as in the case of pbspro
    jid2=$(tail -n 1 $odir/logs/submission.log  | cut -f 3 -d ' ')
    echo "Started job $jid2 writing to $odir. You will receive an email"
    bam2=$odir/out/$SAMPLE/star/${SAMPLE}_hg19_Aligned.sortedByCoord.out.bam

    jobname="${pipeline}.${MYNAME}.check.SE"
    mailopt="-M $(toaddr) -m bea"
    if qstat --version 2>&1 | grep -q PBSPro; then
        # -cwd not available but all paths are absolute so no need
        # using bash after -- doesn't work: binary expected
        qsub="qsub -q production -l select=1:ncpus=1 -l select=1:mem=1g -l walltime=175:00:00 -j oe -V $mailopt -N $jobname -W depend=afterok:$jid1:$jid2 --"
    else
        qsub="qsub -pe OpenMP 1 -l mem_free=1G -l h_rt=01:00:00 -j y -b y -cwd -V $mailopt -N $jobname -hold_jid $jid1,$jid2"
    fi
    echo "Starting comparison between outputs" | tee -a $log
    echo "Will run (hold job) $(pwd)/test_num_reads.sh $bam1 $bam2 500000 1000000" | tee -a $log
    $qsub "$(pwd)/test_num_reads.sh $bam1 $bam2 500000 1000000" >> $log 2>&1


    
    echo "Real run: 1 1M PE fastq pair" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}.XXXXXXXXXX) && rmdir $odir
    eval $CMD_1_PE_1M -o $odir -v >> $log 2>&1
    # magically works even if line just contains id as in the case of pbspro
    jid1=$(tail -n 1 $odir/logs/submission.log  | cut -f 3 -d ' ')
    echo "Started job $jid1 writing to $odir. You will receive an email"    
    bam1=$odir/out/$SAMPLE/star/${SAMPLE}_hg19_Aligned.sortedByCoord.out.bam

    echo "Real run: 2 500K PE fastq pairs" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}.XXXXXXXXXX) && rmdir $odir
    eval $CMD_2_PE_500K -o $odir -v >> $log 2>&1
    # magically works even if line just contains id as in the case of pbspro
    jid2=$(tail -n 1 $odir/logs/submission.log  | cut -f 3 -d ' ')
    echo "Started job $jid2 writing to $odir. You will receive an email"
    bam2=$odir/out/$SAMPLE/star/${SAMPLE}_hg19_Aligned.sortedByCoord.out.bam

    jobname="${pipeline}.${MYNAME}.check.PE"
    mailopt="-M $(toaddr) -m bea"
    if qstat --version 2>&1 | grep -q PBSPro; then
        # -cwd not available but all paths are absolute so no need
        # using bash after -- doesn't work: binary expected
        qsub="qsub -q production -l select=1:ncpus=1 -l select=1:mem=1g -l walltime=175:00:00 -j oe -V $mailopt -N $jobname -W depend=afterok:$jid1:$jid2 --"
    else
        qsub="qsub -pe OpenMP 1 -l mem_free=1G -l h_rt=01:00:00 -j y -b y -cwd -V $mailopt -N $jobname -hold_jid $jid1,$jid2"
    fi
    echo "Starting comparison between outputs" | tee -a $log
    echo "Will run (hold job) $(pwd)/test_num_reads.sh $bam1 $bam2 1000000 2000000" | tee -a $log
    $qsub "$(pwd)/test_num_reads.sh $bam1 $bam2 1000000 2000000" >> $log 2>&1


    if [ $SKIP_REAL_FULL -eq 0 ]; then
        echo "Real run: Full" | tee -a $log
        odir=$(mktemp -d ${test_outdir_base}.XXXXXXXXXX) && rmdir $odir
        eval $CMD_FULL -o $odir -v >> $log 2>&1
        # magically works even if line just contains id as in the case of pbspro
        jid=$(tail -n 1 $odir/logs/submission.log  | cut -f 3 -d ' ')
        echo "Started job $jid writing to $odir. You will receive an email"
    else
        echo "Skipping real full run due to config"
    fi
        
else
    echo "Real-run test skipped"
fi


echo
echo "$COMPLETE_MSG"

