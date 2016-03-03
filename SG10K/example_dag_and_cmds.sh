#!/bin/bash
set -euo pipefail;

wrapper=$(readlink -f $(dirname $0)/SG10K.py)
outdir=$(dirname $wrapper)

FASTQ_DIR="$RPD_ROOT/testing/data/SG10K/illumina-platinum-NA12878/"
test -d $FASTQ_DIR
fastqs_1=$(ls $FASTQ_DIR/*ERR091571_1*1M-only.fastq.gz)
fastqs_2=$(ls $FASTQ_DIR/*ERR091571_2*1M-only.fastq.gz)

tmpdir=$(mktemp -d)
rm -rf $tmpdir
$wrapper -1 $fastqs_1 -2 $fastqs_2 --sample example -o $tmpdir --no-run


cd $tmpdir;
EXTRA_SNAKEMAKE_ARGS="--dryrun --quiet --dag" bash run.sh  | dot -Tpdf > $outdir/example_workflow_graph.pdf 
EXTRA_SNAKEMAKE_ARGS="--dryrun --quiet --printshellcmds" bash run.sh | cut -f 2 -d ']' > $outdir/example_workflow_commands.txt

test -d $tmpdir && rm -rf $tmpdir
