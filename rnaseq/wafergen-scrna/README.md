# wafergen-scrna

## Summary

This pipeline preprocess and analyses paired-end single-cell RNA-seq
data and supports universal molecular identifiers (UMI) based
single-cell RNA-seq analyses, following the WaferGen’s ICELL8 single
cell sequencing data sets on the Illumina platform. This pipeline uses
[umis](https://github.com/vals/umis) and [scRNApipe](https://github.com/MarinusVL/scRNApipe)
for the core analysis.

In a first step reads are quality trimmed and adapter sequences are
removed (both achieved with Skewer). Facilitated by scRNApipe,
reads are further processed by the umis packages. The preprocessed reads
are aligned by two different methods  1. with STAR against the given
reference and 2. with Kallisto against the transcripts.  The mapped bam files from STAR aligner are
deduplicated (default) and metafeatures (genes) are counted using
featurecounts. The pseudo-aligned reads with transcripts are counted
by unique UMI (gene-UMI). The analysis provides the expression
matrix of gens and transcripts for cell barcodes.

The pipeline also provides generic stats, coverage, mappability,
MultiQC, RNA-SeQC (per cellular barcode) and FastQC output.


## Input:

Cellular barcode list (see option `-c`): All samples barcodes must be
listed in this file (for non-demux use "1")

See cfg/references.yaml (listing reference genome, index, annotation
and gene id files) for reference data used by default (also refer to
option `--references-cfg`).

In addition you will need to provide sample definitions, either
through a config file (`--sample-cfg`) or through a full definition on
the commandline (options `-1`, `-2` and `-s`).

## Output:

The following lists the most important files/directories that are
created per sample in correspondingly named subfolders of `out`:

- `Results/gene_ExpressionMatrix.csv`: Expression matrix from STAR aligned BAM file
- `kallisto/kallisto.tagcount.txt`: Expression matrix by Kallisto
- `mb-histogram.txt` Number of of raw reads from each cell barcode-UMI
- `cb-histogram.txt` Number of of raw reads from each cell barcode

Reports:
- `Reports/FinalReport.html`: MultiQC output
- `Reports//QCreports/{sample}_fastqc.html`: FastQC output
- `Reports/SummarisedStats.csv`: Summary stats of reads preprocessing, STAR, featurecount, dedup logs etc.

## References

- scRNApipe: [website](https://github.com/MarinusVL/scRNApipe)
- umis: [website](https://github.com/vals/umis)
- Kallisto [website](https://pachterlab.github.io/kallisto/about) and [publication](https://www.ncbi.nlm.nih.gov/pubmed/27043002)
- Skewer: [publication](https://www.ncbi.nlm.nih.gov/pubmed/24925680) and [website](https://github.com/relipmoc/skewer)
