#!/bin/bash

# compare precomputed fastq properties to the test fastq files
# see also testing/data/bcl2fastq/README.md

expf=$1
# e.g. /mnt/projects/rpd/testing/data/bcl2fastq/HS001-PE-R000296_AH3VF3BCXX.exp.txt
outd=$2
# e.g. /mnt/projects/rpd/testing/output/bcl2fastq-commit-a033a0c-dirty-HS001-PE-R000296_AH3VF3BCXX.TXYH43HzvS/out/ 


test -z "$outd" && exit 1
test -z "$expf" && exit 1
test -e "$outd" || exit 1
test -e "$expf" || exit 1

ls -d $outd/Project_* || exit 1

testf=$outd/fq_test_vs_exp.txt
for f in $(find $outd/Project_*/Sample_*/ -name \*fastq.gz); do
    echo -n "$f ";  echo $(zcat $f | wc -l)/4 | bc;
done | sed 's,.*/Proj,Proj,' | sort -k 1 > $testf

diff -u $testf $expf || exit 1
echo "All entries match"

