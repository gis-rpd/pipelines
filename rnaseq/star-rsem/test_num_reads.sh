#!/bin/bash

# make sure two bams have the same number of reads
# and that this number is within given range

bam1=$1
bam2=$2
minr=$3
maxr=$4

test -z "$bam1" && exit 1
test -z "$bam2" && exit 1
if [ ! -e "$bam1" ] || [ ! -e "$bam2" ]; then
    echo "FATAL: non-existing input files ($bam1 and/or $bam2)" 1>&2
    exit 1
fi
if [ -z "$minr" ] || [ -z "$maxr" ]; then
    echo "FATAL: no range given" 1>&2
    exit 1
fi


function bam_num_reads() {
    # bam needs to be indexed
    local bam=$1
    samtools idxstats $bam | awk '{s+=$3; s+=$4} END {print s}'
}

num_reads_1=$(bam_num_reads $bam1)
num_reads_2=$(bam_num_reads $bam2)
if [ $num_reads_1 -ne $num_reads_2 ]; then
    echo "FATAL: number of reads differ between $bam1 and $bam2" 1>&2
    exit 1
fi
if [ $num_reads_1 -lt $minr ] || [ $num_reads_1 -gt $maxr ]; then
    echo "FATAL: number of reads ($num_reads_1) outside allowed range ($minr<=x<=$maxr)" 1>&2
    exit 1
fi
echo "OK"



