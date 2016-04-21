#!/bin/bash

# http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euo pipefail

MYNAME=$(basename $(readlink -f $0))

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


test -z "$RPD_ROOT" && exit 1
TEST_SEQ_RUN_DIRS="$RPD_ROOT/testing/data/bcl2fastq/MS001-PE-R00294_000000000-AH2G7"
TEST_SEQ_RUN_DIRS="$TEST_SEQ_RUN_DIRS $RPD_ROOT/testing/data/bcl2fastq/NS001-SR-R00139_HKWHTBGXX"
TEST_SEQ_RUN_DIRS="$TEST_SEQ_RUN_DIRS $RPD_ROOT/testing/data/bcl2fastq/HS001-PE-R000296_AH3VF3BCXX"
TEST_SEQ_RUN_DIRS="$TEST_SEQ_RUN_DIRS $RPD_ROOT/testing/data/bcl2fastq/HS004-PE-R00138_AC6A7EANXX"
TEST_SEQ_RUN_DIRS="$TEST_SEQ_RUN_DIRS $RPD_ROOT/testing/data/bcl2fastq/HS007-PE-R00020_BH5THFBBXX"
for d in $TEST_SEQ_RUN_DIRS; do
    if [ ! -d $d ]; then
        echo "FATAL: Run directory $d missing" 1>&2
    fi
done
  
cd $(dirname $0)
pipeline=$(pwd | sed -e 's,.*/,,')
commit=$(git describe --always --dirty)
test -e Snakefile || exit 1


test_outdir_base=/mnt/projects/rpd/testing/output/
log=$(mktemp)
COMPLETE_MSG="*** All tests completed ***"
echo "Logging to $log"
echo "Check log if the following final message is not printed: \"$COMPLETE_MSG\""


# dryruns
#
if [ $skip_dry_runs -ne 1 ]; then
    echo "Dryrun: bcl2fastq_cronjob.py" | tee -a $log
    ./bcl2fastq_cronjob.py -n -1 >> $log 2>&1 

    for d in $TEST_SEQ_RUN_DIRS; do
        echo "Dryrun: bcl2fastq.py dryrun for $d" | tee -a $log
        odir=$(mktemp -d $test_outdir_base/${pipeline}-commit-${commit}-$(echo $d | sed -e 's,.*/,,').XXXXXXXXXX) && rmdir $odir

        ./bcl2fastq.py -d $d -o $odir --no-run -t >> $log 2>&1
        pushd $odir >> $log
        EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
        rm -rf $odir
        popd >> $log
    done
    echo "Dryrun tests successfully completed"
else
    echo "Dryruns tests skipped"
fi

# real runs
#
if [ $skip_real_runs -ne 1 ]; then
    for d in $TEST_SEQ_RUN_DIRS; do
    	if echo $d | grep -q HS007-PE-R00020_BH5THFBBXX; then
    	    echo "FIXME skipping HS007-PE-R00020_BH5THFBBXX" 1>&2
    	    continue
    	fi
        echo "Real run: bcl2fastq.py for $d" | tee -a $log
        odir=$(mktemp -d $test_outdir_base/${pipeline}-commit-${commit}-$(echo $d | sed -e 's,.*/,,').XXXXXXXXXX) && rmdir $odir
        ./bcl2fastq.py -d $d -o $odir -t >> $log 2>&1
        jid=$(tail -n 1 $odir/logs/submission.log  | cut -f 3 -d ' ')
        echo "Started $jid writing to $odir"

        exp=$(ls /mnt/projects/rpd/testing/data/bcl2fastq/*exp.txt | grep $(basename $d))
        jobname="${pipeline}.${MYNAME}.check.$(basename $d)"
        qsub="qsub -pe OpenMP 1 -l mem_free=1G -l h_rt=01:00:00 -j y -V -b y -cwd -m bea  -N $jobname -hold_jid $jid"
        echo $qsub "bash test_cmp_in_and_out.sh $exp $odir"
    done
    echo "Real-runs tests started. Checking will be performed later"
else
    echo "Real-run test skipped"
fi


echo
echo "$COMPLETE_MSG"
