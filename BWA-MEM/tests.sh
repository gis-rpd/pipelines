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
NA12878_DIR=$RPD_ROOT/testing/data/SG10K/illumina-platinum-NA12878
# naming: RXSY = Read X Split Y
R1S1=$NA12878_DIR/ERR091571_1_split000001_1konly.fastq.gz
R2S1=$NA12878_DIR/ERR091571_2_split000001_1konly.fastq.gz
RANDR1=$NA12878_DIR/ERR091571_1_rand1k.fastq.gz
RANDR2=$NA12878_DIR/ERR091571_1_rand1k.fastq.gz
RANDR1WDUPS=$NA12878_DIR/ERR091571_1_rand1k.dups.fastq.gz
RANDR2WDUPS=$NA12878_DIR/ERR091571_2_rand1k.dups.fastq.gz
SPLIT1KONLY_PE_CFG=$NA12878_DIR/split1konly_pe.yaml
SPLIT1KONLY_SR_CFG=$NA12878_DIR/split1konly_sr.yaml

REFFA=$RPD_ROOT/genomes.testing/human_g1k_v37/human_g1k_v37.fasta

for f in $R1S1 $R2S1 $RANDR1 $RANDR2 $RANDR1WDUPS $RANDR2WDUPS $REFFA $SPLIT1KONLY_PE_CFG $SPLIT1KONLY_SR_CFG ; do
    if [ ! -e $f ]; then
        echo "FATAL: non existant file $f" 1>&2
        exit 1
    fi
done


cd $(dirname $0)
pipeline=$(pwd | sed -e 's,.*/,,')
commit=$(git describe --always --dirty)
test -e Snakefile || exit 1


test_outdir_base=/mnt/projects/rpd/testing/output/${pipeline}/${pipeline}-commit-${commit}
log=$(mktemp)
COMPLETE_MSG="*** All tests completed ***"
echo "Logging to $log"
echo "Check log if the following final message is not printed: \"$COMPLETE_MSG\""


# dryruns
#
if [ $skip_dry_runs -ne 1 ]; then
    echo "Dryrun: PE on command line" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}-pe-cmdline.XXXXXXXXXX) && rmdir $odir
    ./BWA-MEM.py -1 $R1S1 -2 $R2S1 -s NA12878 -r $REFFA -d -o $odir --no-run >> $log 2>&1
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
    echo "Real run: checking whether SE reads in == reads out (-secondary)" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}-se-in-eq-out.XXXXXXXXXX) && rmdir $odir
    ./BWA-MEM.py --no-mail -1 $R1S1 -s NA12878 -r $REFFA -d -o $odir --no-run >> $log 2>&1
    pushd $odir >> $log
    bash run.sh >> $log 2>&1
    popd >> $log
    bam=$(ls $odir/out/*bam)
    # remove secondary alignments (assuming -M otherwise it's supplementary)
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
    odir=$(mktemp -d ${test_outdir_base}-pe-in-eq-out.XXXXXXXXXX) && rmdir $odir
    ./BWA-MEM.py --no-mail -1 $R1S1 -2 $R2S1 -s NA12878 -r $REFFA -d -o $odir --no-run >> $log 2>&1
    pushd $odir >> $log
    bash run.sh >> $log 2>&1
    popd >> $log
    bam=$(ls $odir/out/*bam)
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
    odir=$(mktemp -d ${test_outdir_base}-pe-mdups.XXXXXXXXXX) && rmdir $odir
    ./BWA-MEM.py --no-mail -v -1 $RANDR1WDUPS -2 $RANDR2WDUPS -s NA12878 -r $REFFA -d -o $odir --no-run >> $log 2>&1
    pushd $odir >> $log
    bash run.sh >> $log 2>&1
    popd >> $log
    bam=$(ls $odir/out/*bam)
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

    echo "Real run: dups marking not set should not mark dups" | tee -a $log
    odir=$(mktemp -d ${test_outdir_base}-pe-no-mdups.XXXXXXXXXX) && rmdir $odir
    ./BWA-MEM.py --no-mail -v -1 $RANDR1WDUPS -2 $RANDR2WDUPS -s NA12878 -r $REFFA -o $odir --no-run >> $log 2>&1
    pushd $odir >> $log
    bash run.sh >> $log 2>&1
    popd >> $log
    bam=$(ls $odir/out/*bam)
    ndups=$(samtools view -f 0x400 -c $bam)
    if [ $ndups -gt 0 ]; then
        echo "ERROR number of dups ($ndups) should have been zero in $bam" | tee -a $log
        exit 1
    else
        echo "OK" | tee -a $log
    fi
    rm -rf $odir
    
else
    echo "Real-run test skipped"
fi


echo
echo "$COMPLETE_MSG"
