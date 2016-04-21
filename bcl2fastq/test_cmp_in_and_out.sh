#!/bin/bash

# compare precomputed fastq properties to the test fastq files
# see also testing/data/bcl2fastq/README.md
# assumes we have fastqc output already (which is part of the pipeline)

expf=$1
# e.g. /mnt/projects/rpd/testing/data/bcl2fastq/HS001-PE-R000296_AH3VF3BCXX.exp.txt
outd=$2
# e.g. /mnt/projects/rpd/testing/output/bcl2fastq-commit-a033a0c-dirty-HS001-PE-R000296_AH3VF3BCXX.TXYH43HzvS/
# just one above ./out and ./logs etc

test -z "$outd" && exit 1
test -z "$expf" && exit 1
test -e "$outd" || exit 1
test -e "$expf" || exit 1

ls -d $outd/out/Project_* || exit 1

testf=$outd/out/fq_test_vs_exp.txt
# reference to Project and sample is a bit paranoid. Would work on parent directory a well
for fqc in $(find $outd/out/Project_*/Sample_*/ -name \*fastqc.zip); do
    fq=${fqc%_fastqc.zip}.fastq.gz;
    nreads=$(unzip -p $fqc \*fastqc_data.txt | awk '/Total Sequences/ {print $NF}');
    echo $(echo $fq | sed -e 's,.*Project_,Project_,') $nreads;
done | sed 's,.*Proj,Proj,' | sort -k 1 > $testf

if ! diff -u $testf $expf >/dev/null; then
    echo "ERROR Entries differ (compare $testf with expected $expf)" 1>&2
    exit 1
fi
echo "OK: All entries match"

