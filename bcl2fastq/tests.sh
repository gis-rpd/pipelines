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


test -z "$RPD_ROOT" && exit 1

TEST_SEQ_RUN_DIRS="$RPD_ROOT/testing/data/bcl2fastq/MS001-PE-R00294_000000000-AH2G7"
TEST_SEQ_RUN_DIRS="$TEST_SEQ_RUN_DIRS $RPD_ROOT/testing/data/bcl2fastq/NS001-SR-R00139_HKWHTBGXX"
TEST_SEQ_RUN_DIRS="$TEST_SEQ_RUN_DIRS $RPD_ROOT/testing/data/bcl2fastq/HS001-PE-R000296_AH3VF3BCXX"
TEST_SEQ_RUN_DIRS="$TEST_SEQ_RUN_DIRS $RPD_ROOT/testing/data/bcl2fastq/HS004-PE-R00138_AC6A7EANXX"
if false; then
    echo "WARN: Ignoring HS007" 1>&2
else
    TEST_SEQ_RUN_DIRS="$TEST_SEQ_RUN_DIRS $RPD_ROOT/testing/data/bcl2fastq/HS007-PE-R00020_BH5THFBBXX"
fi
if false; then
    echo "MS001 only" 1>&2
    TEST_SEQ_RUN_DIRS="$RPD_ROOT/testing/data/bcl2fastq/MS001-PE-R00294_000000000-AH2G7"
fi
if false; then
    echo "HS004 only" 1>&2
    TEST_SEQ_RUN_DIRS="$RPD_ROOT/testing/data/bcl2fastq/HS004-PE-R00138_AC6A7EANXX"
fi


for d in $TEST_SEQ_RUN_DIRS; do
    if [ ! -d $d ]; then
        echo "FATAL: Run directory $d missing" 1>&2
    fi
done
  
rootdir=$(readlink -f $(dirname $0))
cd $rootdir
pipeline=$(pwd | sed -e 's,.*/,,')
commit=$(git describe --always --dirty)
test -e Snakefile || exit 1


test_outdir_base=$RPD_ROOT/testing/output/$pipeline/
log=$(mktemp)
COMPLETE_MSG="*** All tests completed ***"
echo "Starting tests"
echo "Logging to $log"
echo "Check log if the following final message is not printed: \"$COMPLETE_MSG\""
if [ $skip_real_runs -ne 1 ]; then
    echo "Also check log if the check against expected output hold jobs fail"
fi

# DAG
d=$(echo $TEST_SEQ_RUN_DIRS | cut -f1 -d ' ')
echo "DAG: bcl2fastq.py for $d" | tee -a $log
odir=$(mktemp -d $test_outdir_base/${pipeline}-commit-${commit}-$(echo $d | sed -e 's,.*/,,').XXXXXXXXXX) && rmdir $odir
./bcl2fastq.py -d $d -o $odir --no-run -t >> $log 2>&1
pushd $odir >> $log
type=pdf;
EXTRA_SNAKEMAKE_ARGS="--dag" bash run.sh; cat logs/snakemake.log | dot -T$type > dag.$type
echo "DEBUG: rootdir=$rootdir pwd=$(pwd)"
cp dag.$type $rootdir
popd >> $log
rm -rf $odir
exit 1

# dryruns
#
if [ $skip_dry_runs -ne 1 ]; then
    echo "Dryrun: mongo_status.py fake run" 1>&2
    iso8601ns=$(date --iso-8601=ns | tr ':,' '-.');
    iso8601ms=${iso8601ns:0:26}
    ./mongo_status.py -r FAKERUN_FAKEFLOWCELL -a $iso8601ms -s SUCCESS -t -v

    
    echo "Dryrun: mongo_status_per_mux.py fake run" 1>&2
    iso8601ns=$(date --iso-8601=ns | tr ':,' '-.');
    iso8601ms=${iso8601ns:0:26}
    ./mongo_status_per_mux.py -r FAKERUN_FAKEFLOWCELL -a $iso8601ms -i FAKE -d /tmp/FAKE -s FAILED -t -v
    

    echo "Dryrun: bcl2fastq_starter.py" | tee -a $log
    ./bcl2fastq_starter.py -n -1 -v >> $log 2>&1 

    
    echo "Dryrun: bcl2fastq_dbupdate.py" | tee -a $log
    ./bcl2fastq_dbupdate.py -n -t -v >> $log 2>&1


    r="MS001-PE-R00315_000000000-ANBGU"
    echo "Dryrun: Testing failed seq run $r"  | tee -a $log
    odir=$(mktemp -d $test_outdir_base/${pipeline}-commit-${commit}-$(echo $r | sed -e 's,.*/,,').XXXXXXXXXX) && rmdir $odir
    ./bcl2fastq.py -r $r -o $odir --no-run -t >> $log 2>&1
    if [ ! -e "$odir"/SEQRUNFAILED ]; then
        echo "ERROR: $r should have failed but flag file missing in $odir" | tee -a $log
        exit 1
    fi

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
        echo "Real run: bcl2fastq.py for $d" | tee -a $log
        odir=$(mktemp -d $test_outdir_base/${pipeline}-commit-${commit}-$(echo $d | sed -e 's,.*/,,').XXXXXXXXXX) && rmdir $odir
        ./bcl2fastq.py -d $d -o $odir --name "test:$(basename $d)" -t >> $log 2>&1
        # magically works even if line just contains id as in the case of pbspro
        jid=$(tail -n 1 $odir/logs/submission.log  | cut -f 3 -d ' ')
        echo "Started $jid writing to $odir"

        exp=$(ls $RPD_ROOT/testing/data/bcl2fastq/*exp.txt | grep $(basename $d))
        jobname="${pipeline}.${MYNAME}.check.$(basename $d)"
        mailopt="-M $(toaddr) -m bea"
        if qstat --version 2>&1 | grep -q PBSPro; then
            # -cwd not available but all paths are absolute so no need
            # using bash after -- doesn't work: binary expected
            qsub="qsub -q production -l select=1:ncpus=1 -l select=1:mem=1g -l walltime=175:00:00 -j oe -V $mailopt -N $jobname -W depend=afterok:$jid --"
        else
            qsub="qsub -pe OpenMP 1 -l mem_free=1G -l h_rt=01:00:00 -j y -b y -cwd -V $mailopt -N $jobname -hold_jid $jid"
        fi
        echo "Starting comparison against expected output" | tee -a $log
        echo "Will run (hold job) $(pwd)/test_cmp_in_and_out.sh $exp $odir" | tee -a $log
        $qsub "$(pwd)/test_cmp_in_and_out.sh $exp $odir" >> $log 2>&1
    done
    echo "Real-runs tests started. Checking will be performed later."
else
    echo "Real-run test skipped"
fi


echo
echo "$COMPLETE_MSG"
