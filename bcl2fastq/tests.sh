#!/bin/bash

# http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euo pipefail


usage() {
    MYNAME=$(basename $(readlink -f $0))
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


TEST_SEQ_RUN_DIRS="../../../../testing/data/bcl2fastq/MS001-PE-R00294_000000000-AH2G7"
TEST_SEQ_RUN_DIRS="$TEST_SEQ_RUN_DIRS ../../../../testing/data/bcl2fastq/NS001-SR-R00139_HKWHTBGXX"
TEST_SEQ_RUN_DIRS="$TEST_SEQ_RUN_DIRS ../../../../testing/data/bcl2fastq/HS001-PE-R000296_AH3VF3BCXX"
TEST_SEQ_RUN_DIRS="$TEST_SEQ_RUN_DIRS ../../../../testing/data/bcl2fastq/HS004-PE-R00138_AC6A7EANXX"
TEST_SEQ_RUN_DIRS="$TEST_SEQ_RUN_DIRS ../../../../testing/data/bcl2fastq/HS007-PE-R00020_BH5THFBBXX"
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
echo "Logging to $log. Check if exit status if non 0"


# dryruns
#
if [ $skip_dry_runs -ne 1 ]; then
    echo "Dryrun: bcl2fastq_cronjob.py" | tee -a $log
    ./bcl2fastq_cronjob.py -n -1 >> $log 2>&1 

    for d in $TEST_SEQ_RUN_DIRS; do
        echo "Dryrun: bcl2fastq.py dryrun for $d" | tee -a $log
        odir=$(mktemp -d) && rmdir $odir
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
        echo "Real run: bcl2fastq.py for $d" | tee -a $log
        odir=$(mktemp -d $test_outdir_base/${pipeline}-commit-${commit}-$(echo $d | sed -e 's,.*/,,').XXXXXXXXXX) && rmdir $odir
        echo "FIXME odir=$odir" 1>&2
        
        ./bcl2fastq.py -d $d -o $odir -t >> $log 2>&1
        jid=$(tail -n 1 $odir/logs/submission.log  | cut -f 3 -d ' ')
        echo "Started $jid writing to $odir"
        echo "FIXME NotImplementedError: check output once jid is completed (check job using hold id?) successfully and clean up" 1>&2;
        echo "FIXME NotImplementedError: Use bash test_cmp_in_and_out.sh, e.g. with /mnt/projects/rpd/testing/data/bcl2fastq/HS001-PE-R000296_AH3VF3BCXX.exp.txt  /mnt/projects/rpd/testing/output/bcl2fastq-commit-97af0ba.3YKYp5owDW/out" 1>&2;
        echo "FIXME break" 1>&2; break
    done
    echo "Real-runs tests started. Checking will be performed later"
else
    echo "Real-run test skipped"
fi
