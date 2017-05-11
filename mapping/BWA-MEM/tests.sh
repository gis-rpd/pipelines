#!/bin/bash

# FIXME reimplement in python

# http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euo pipefail

MYNAME=$(basename $(readlink -f $0))
PIPELINE=$(basename $(dirname $(readlink -f $0)))
DOWNSTREAM_OUTDIR_PY=$(readlink -f $(dirname $MYNAME)/../../tools/downstream_outdir.py)


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


module load samtools


# readlink resolves links and makes path absolute
test -z "$RPD_ROOT" && exit 1
NA12878_DIR=$RPD_ROOT/testing/data/illumina-platinum-NA12878
# naming: RXSY = Read X Split Y
R1S1=$NA12878_DIR/ERR091571_1_split000001_1konly.fastq.gz
R2S1=$NA12878_DIR/ERR091571_2_split000001_1konly.fastq.gz
RANDR1=$NA12878_DIR/ERR091571_1_rand1k.fastq.gz
RANDR2=$NA12878_DIR/ERR091571_1_rand1k.fastq.gz
RANDR1WDUPS=$NA12878_DIR/ERR091571_1_rand1k.dups.fastq.gz
RANDR2WDUPS=$NA12878_DIR/ERR091571_2_rand1k.dups.fastq.gz
SPLIT1KONLY_PE_CFG=$NA12878_DIR/split1konly_pe.yaml
SPLIT1KONLY_SR_CFG=$NA12878_DIR/split1konly_sr.yaml
SPLIT1KONLY_2SAMPLE_CFG=$NA12878_DIR/split1konly_2sample.yaml
SAMPLE=NA12878


for f in $R1S1 $R2S1 $RANDR1 $RANDR2 $RANDR1WDUPS $RANDR2WDUPS $SPLIT1KONLY_PE_CFG $SPLIT1KONLY_SR_CFG ; do
    if [ ! -e $f ]; then
        echo "FATAL: non existant file $f" 1>&2
        exit 1
    fi
done


rootdir=$(readlink -f $(dirname $0))
cd $rootdir
pipeline=$(pwd | sed -e 's,.*/,,')
commit=$(git describe --always --dirty)
test -e Snakefile || exit 1


log=$(mktemp)
COMPLETE_MSG="*** All tests completed ***"
echo "Logging to $log"
echo "Check log if the following final message is not printed: \"$COMPLETE_MSG\""


# DAG
SKIP_DAG=1
if [ $SKIP_DAG -eq 0 ]; then
    echo "DAG: PE through config" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    ./BWA-MEM.py --sample-cfg $SPLIT1KONLY_PE_CFG -o $odir --no-run >> $log 2>&1
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
    echo "Dryrun: PE on command line" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    ./BWA-MEM.py -1 $R1S1 -2 $R2S1 -s $SAMPLE -o $odir --no-run >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    rm -rf $odir
    popd >> $log

    echo "Dryrun: PE through config" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    ./BWA-MEM.py --sample-cfg $SPLIT1KONLY_PE_CFG -o $odir --no-run >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    rm -rf $odir
    popd >> $log

    echo "Dryrun: SR on command line" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    ./BWA-MEM.py -1 $R1S1 -s $SAMPLE -o $odir --no-run >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    rm -rf $odir
    popd >> $log
    
    echo "Dryrun: SR through config" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    ./BWA-MEM.py --sample-cfg $SPLIT1KONLY_SR_CFG -o $odir --no-run >> $log 2>&1
    pushd $odir >> $log
    EXTRA_SNAKEMAKE_ARGS="--dryrun" bash run.sh >> $log 2>&1
    rm -rf $odir
    popd >> $log

    echo "Dryrun: 2-sample config" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    ./BWA-MEM.py --sample-cfg $SPLIT1KONLY_2SAMPLE_CFG -o $odir --no-run >> $log 2>&1
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
    echo "Real run: checking whether SE reads in == reads out (-secondary)" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    ./BWA-MEM.py --no-mail -1 $R1S1 -s $SAMPLE -o $odir --no-run >> $log 2>&1
    pushd $odir >> $log
    bash run.sh >> $log 2>&1
    popd >> $log
    bam=$(ls $odir/out/$SAMPLE/*dedup.bam)
    # remove secondary alignments (assuming -M otherwise it's supplementary)
    #echo "DEBUG bam=$bam" 1>&2
    nreadsbam=$(samtools view -F 0x100 -c $bam)
    nreadsfq=$(echo $(zcat $R1S1 | wc -l)/4 | bc)
    if [ $nreadsbam -ne $nreadsfq ]; then
        echo "ERROR number of (non-secondary) reads in bam ($nreadsbam) differs from fastq ($nreadsfq)" | tee -a $log
        exit 1
    else
        echo "OK" | tee -a $log
    fi
    rm -rf $odir

    echo "Real run: checking whether PE reads in == reads out (-secondary)" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    ./BWA-MEM.py --no-mail -1 $R1S1 -2 $R2S1 -s $SAMPLE -o $odir --no-run >> $log 2>&1
    pushd $odir >> $log
    bash run.sh >> $log 2>&1
    popd >> $log
    bam=$(ls $odir/out/$SAMPLE/*dedup.bam)
    #echo "DEBUG bam=$bam" 1>&2
    # remove secondary alignments (assuming -M otherwise it's supplementary)
    nreadsbam=$(samtools view -F 0x100 -c $bam)
    nreadsfq=$(echo $(zcat $R1S1 $R2S1 | wc -l)/4 | bc)
    if [ $nreadsbam -ne $nreadsfq ]; then
        echo "ERROR number of (non-secondary) reads in bam ($nreadsbam) differs from fastq ($nreadsfq)" | tee -a $log
        exit 1
    else
        echo "OK" | tee -a $log
    fi
    rm -rf $odir

    echo "Real run: checking whether PE dup reads are removed" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    ./BWA-MEM.py --no-mail -v -1 $RANDR1WDUPS -2 $RANDR2WDUPS -s $SAMPLE -o $odir --no-run >> $log 2>&1
    pushd $odir >> $log
    bash run.sh >> $log 2>&1
    popd >> $log
    bam=$(ls  $odir/out/$SAMPLE/*dedup.bam)
    #echo "DEBUG bam=$bam" 1>&2
    # count only dups in bam
    ndups=$(samtools view -f 0x400 -c $bam)
    # nondups from non dup input
    nnondups=$(echo $(zcat $RANDR1 $RANDR2 | wc -l)/4 | bc)
    ndiff=$(echo $ndups-$nnondups | bc | tr -d '-')
    alloweddelta=100
    if [ $ndiff -gt $alloweddelta ]; then
        echo "ERROR number of dups ($ndups) and nondups ($nnondups) differ ($ndiff>$alloweddelta) too much in $bam" | tee -a $log
        exit 1
    else
        echo "OK" | tee -a $log
    fi
    rm -rf $odir

    echo "Real run: no dups marking should not mark dups" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    ./BWA-MEM.py --no-mail -v -1 $RANDR1WDUPS -2 $RANDR2WDUPS -s $SAMPLE -D -o $odir --no-run >> $log 2>&1
    pushd $odir >> $log
    bash run.sh >> $log 2>&1
    popd >> $log
    bam=$(ls $odir/out/$SAMPLE/*bam)
    ndups=$(samtools view -f 0x400 -c $bam)
    if [ $ndups -gt 0 ]; then
        echo "ERROR number of dups ($ndups) should have been zero in $bam" | tee -a $log
        exit 1
    else
        echo "OK" | tee -a $log
    fi
    rm -rf $odir

    echo "Real run: 2-sample config" | tee -a $log
    odir=$($DOWNSTREAM_OUTDIR_PY -r $(whoami) -p $PIPELINE)
    ./BWA-MEM.py --no-mail --sample-cfg $SPLIT1KONLY_2SAMPLE_CFG -o $odir --no-run >> $log 2>&1
    pushd $odir >> $log
    bash run.sh >> $log 2>&1
    popd >> $log
    bams=$(ls $odir/out/*/*dedup.bam)
    nbams=$(echo $bams | wc -w)
    if [ "$nbams" -ne 2 ]; then
        echo "ERROR expected two bams but go $nbams" | tee -a $log
        exit 1
    else
        echo "OK" | tee -a $log
    fi
    # Test number of reads in both BAM files?
    rm -rf $odir

else
    echo "Real-run test skipped"
fi


echo
echo "$COMPLETE_MSG"
