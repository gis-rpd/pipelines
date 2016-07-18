#!/bin/bash
set -euo pipefail;

wrapper=$(readlink -f $(dirname $0)/SG10K.py)
outdir=$(dirname $wrapper)

CFG=$RPD_ROOT/testing/data/SG10K/MUX3275-WHH474.yaml
test -e $CFG

tmpdir=$(mktemp -d)
rmdir $tmpdir
echo "DEBUG: tmpdir is $tmpdir" 1>&2
$wrapper -c $CFG --sample WHH474 -o $tmpdir --no-run

pushd $tmpdir;
dag=$outdir/example_workflow_graph.pdf
echo "Writing DAG to $dag"
EXTRA_SNAKEMAKE_ARGS="--dryrun --quiet --dag" bash run.sh;
cat logs/snakemake.log | dot -Tpdf > $dag
cmds=$outdir/example_workflow_commands.txt
echo "Writing cmds to $cmds"
EXTRA_SNAKEMAKE_ARGS="--dryrun --quiet --printshellcmds" bash run.sh;
cut -f 2 -d ']' logs/snakemake.log > $cmds
popd

if true; then
	echo "DEBUG: not deleting $tmpdir" 1>&2;
else
	test -d $tmpdir && rm -rf $tmpdir;
fi

