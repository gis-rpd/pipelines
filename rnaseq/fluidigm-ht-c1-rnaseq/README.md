# fluidigm-ht-c1-rnaseq

## Summary

This pipeline analyses RNA sequencing data produced with the
[Fluidigm Single cell sequencing C1 mRNA Seq HT](https://www.fluidigm.com/c1openapp/scripthub/script/2015-08/mrna-seq-ht-1440105180550-2)
protocol.

Following conventional bcl2fastq demultiplexing, it uses fluidigm API
script for demultiplexing the row barcodes (N=40) of column samples
using R1 reads. Subsequently R2 reads are poly-A trimmed (with
[prinseq-lite](http://prinseq.sourceforge.net/)) and aligned to given
reference genome using the
[STAR mapper](https://github.com/alexdobin/STAR).

See `cfg/references.yaml` for references used by default (also refer
to option `--references-cfg`). Output of STAR includes the uniquely
mapped genome bam file, transcripts mapped bam file, gene based read
count matrix, wiggle files etc. (see below). For running STAR we
follow recipes given
[here](http://www.rna-seqblog.com/optimizing-rna-seq-mapping-with-star/).

The transcripts/genes expression abundance are estimated by STAR and
[RSEM](http://deweylab.github.io/RSEM/) (reusing STAR's BAM file). The
RSEM results matrix contains mapped reads count and TPM (normalized
value) of genes and isoforms. 

The pipeline also provides generic stats, coverage, mappability, QC
e.g. by running [RNA-SeQC](https://www.broadinstitute.org/cancer/cga/rna-seqc).

Note, STAR is very fast and in order to avoid trouble with STAR's
shared memory option we align samples sequentially.

A word of warning: Please do not use the underscore symbol ("_") in
your sample name, otherwise the fluidigm demultiplexer will crash!

## Output

The following lists the most important files/directories that are
created per sample in correspondingly named subfolders:
  
### STAR

- Mapped genome BAM: `{sample}_{genome}_Aligned.sortedByCoord.out.bam`
- Mapped transcriptome BAM (RSEM input): `{sample}_{genome}_Aligned.toTranscriptome.out.bam`
- Visualization: Wiggle files (`*.wig`)
- Read count (genes): `{sample}_{genome}_ReadsPerGene.out.tab`
- Mappability stats: `{sample}_{genome}_Log.final.out`

Exact STAR mapping parameters can be looked up in the Snakefile.

### RSEM

- Genes expression values with annotation: `{sample}_{genome}_RSEM.genes.results.desc`
- Isoforms expression values with annotation: `{sample}_{genome}_RSEM.isoforms.results.desc`
- Visualization: Wiggle files (`*.wig`)
- Plots: `{sample}_{genome}_RSEM.pdf`

### Picard's CollectRnaSeqMetrics

- Metrics about the RNA-seq alignment:: `{sample}_{genome}_rnaseq-metrics.txt`
- See also http://broadinstitute.github.io/picard/picard-metric-definitions.html#RnaSeqMetrics


### RNA-SeQC (optional)


QC and rate of rRNA and distribution of reads on transcripts:

- `countMetrics.html`
- `metrics.tsv`



