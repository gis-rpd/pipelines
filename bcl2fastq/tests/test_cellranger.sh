#!/bin/bash
set -euo pipefail


# data paths needs to be absolute
TEST_DATA_DIR=$RPD_ROOT/testing/data/cellranger
TINY_BCL_TGZ=$TEST_DATA_DIR/cellranger-tiny-bcl-1.2.0.tar.gz
TINY_BCL_CSV=$TEST_DATA_DIR/cellranger-tiny-bcl-simple-1.2.0.csv
for f in $TINY_BCL_TGZ $TINY_BCL_CSV; do
    if [ ! -e $f ]; then
        echo "ERROR: expected tiny-bcl tarball \"$TINY_BCL_TGZ\" is missing" 1>&2
        exit 1
    fi
done
    
    
MODULES_YAML=../cfg/modules.yaml
mod=$(grep cellranger $MODULES_YAML | tr -d "," | sed -e 's,: *,/,')
set +u;# otherwise we get `_RUN10X: unbound variable`
module load $mod;
set -u
mod=$(grep bcl2fastq $MODULES_YAML | tr -d "," | sed -e 's,: *,/,')
module load $mod;



## testing cellranger binary
#
# according to
# https://support.10xgenomics.com/single-cell-vdj/software/pipelines/latest/using/mkfastq
# `cellranger mkfastq --help returns without errors`
#
echo "TEST: cellranger binary"
cellranger mkfastq --help >/dev/null;


## testing mkfastq with a simple CSV layout file
#
# see https://support.10xgenomics.com/single-cell-gene-expression/software/pipelines/latest/using/mkfastq
#
echo "TEST: mkfastq with a simple CSV layout file"
tinybcl_tmpdir=$(mktemp -d)
out_tmpdir=$(mktemp -dt cellranger-tinybcl-XXXXXX)
run=$tinybcl_tmpdir/$(basename $TINY_BCL_TGZ .tar.gz);# where tar unpacks to
echo "Untarring $TINY_BCL_TGZ to $tinybcl_tmpdir"
tar -C $tinybcl_tmpdir -xzf $TINY_BCL_TGZ
# cellranger will create fastq output (changeeable with --outdir) and a pipestance dir (always PWD) here
# - Cellranger always produces pipestance output in $PWD/$id
# - if --outdir is specified, results (fastq etc) go there
#   otherwise $PWD/$id/outs is used
echo "Running cellranger mkfastq with run $run and csv $TINY_BCL_CSV in $out_tmpdir"
pushd $out_tmpdir
id=tiny-bcl
cellranger mkfastq --id=$id --run=$run --csv=$TINY_BCL_CSV
# paranoia
ls -l $id/outs/qc_summary.json >/dev/null
ls -l $id/outs/fastq_path/*fastq.gz >/dev/null
popd
rm -rf $out_tmpdir


## testing mkfastq with an Illumina Experiment Manager (IEM) sample sheet
#
# see https://support.10xgenomics.com/single-cell-gene-expression/software/pipelines/latest/using/mkfastq
#
# SKIPPED since we don't use IEM sample sheets


echo "COMPLETE"
