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


# readlink resolves links and makes path absolute
test -z "$RPD_ROOT" && exit 1
NA12878_DIR=$RPD_ROOT/testing/data/SG10K/illumina-platinum-NA12878
# naming: RXSY = Read X Split Y
R1S1=$NA12878_DIR/ERR091571_1_split000001_1konly.fastq.gz
R1S2=$NA12878_DIR/ERR091571_1_split000002_1konly.fastq.gz
R1S3=$NA12878_DIR/ERR091571_1_split000003_1konly.fastq.gz
R2S1=$NA12878_DIR/ERR091571_2_split000001_1konly.fastq.gz
R2S2=$NA12878_DIR/ERR091571_2_split000002_1konly.fastq.gz
R2S3=$NA12878_DIR/ERR091571_2_split000003_1konly.fastq.gz

SPLIT1KONLY_PE_CFG=$NA12878_DIR/split1konly_pe.yaml
SPLIT1KONLY_SR_CFG=$NA12878_DIR/split1konly_sr.yaml

REFFA=$(readlink -f ../../../../genomes.testing/human_g1k_v37/human_g1k_v37.fasta)

for f in $R1S1 $R1S2 $R1S3 $R2S1 $R2S2 $R2S3 $REFFA; do
    if [ ! -e $f ]; then
        echo "FATAL: non existant file $f" 1>&2
        exit 1
    fi
done


cd $(dirname $0)
pipeline=$(pwd | sed -e 's,.*/,,')
commit=$(git describe --always --dirty)
test -e Snakefile || exit 1


test_outdir_base=/mnt/projects/rpd/testing/output/${pipeline}-commit-${commit}
log=$(mktemp)
COMPLETE_MSG="*** All tests completed ***"
echo "Logging to $log"
echo "Check log if the following final message is not printed: \"$COMPLETE_MSG\""


# dryruns
#
if [ $skip_dry_runs -ne 1 ]; then
    echo "Dryrun: Testing PE on command line" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}-pe-cmdline.XXXXXXXXXX) && rmdir $odir
    ./BWA-MEM.py -1 $R1S1 -2 $R1S2 -s NA12878 -r $REFFA -d -o $odir --no-run >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    rm -rf $odir
    popd >> $log

    echo "Dryrun: PE through config" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}-pe-config.XXXXXXXXXX) && rmdir $odir
    ./BWA-MEM.py -c $SPLIT1KONLY_PE_CFG -s NA12878 -r $REFFA -d -o $odir --no-run >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    rm -rf $odir
    popd >> $log

    echo "Dryrun: SR on command line" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}-se-cmdline.XXXXXXXXXX) && rmdir $odir
    ./BWA-MEM.py -1 $R1S1 -s NA12878 -r $REFFA -d -o $odir --no-run >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    rm -rf $odir
    popd >> $log
    
    echo "Dryrun: SR through config" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}-se-cmdline.XXXXXXXXXX) && rmdir $odir
    ./BWA-MEM.py -c $SPLIT1KONLY_SR_CFG -s NA12878 -r $REFFA -d -o $odir --no-run >> $log 2>&1
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
    echo " FIXME 
 - check nreads in and out for 1 and two fq pairs
 - check mdups on and off
 - auto test: no/dups,1in/3in
 - number reads in = number reads out
 - make sure samblaster not run if not set through commands and counting of dups
 - check SE input" 1>&2
    
else
    echo "Real-run test skipped"
fi


echo
echo "$COMPLETE_MSG"
