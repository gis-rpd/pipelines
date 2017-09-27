# wafergen-scrna

## Summary

This pipeline analyses WaferGen’s ICELL8 single cell sequencing
data. It uses [umis](https://github.com/vals/umis) and
[scRNApipe](https://github.com/MarinusVL/scRNApipe) for the core
analysis.

In a first step reads are quality trimmed and adapter sequences are
removed (both achieved with Skewer).  Reads are then further processed
by the umis package (facilitated by scRNApipe). The preprocessed reads
are aligned by two different methods
1. with STAR against the given reference genome and
2. with Kallisto against the transcripts.

The mapped BAM files from STAR aligner are deduplicated (user option) and
meta-features (genes) are counted using featurecounts. The
pseudo-aligned reads with transcripts are counted by unique UMI
(gene-UMI). The analysis provides the expression matrix of genes and
transcripts for cell barcodes.

The pipeline also provides generic stats, coverage, mappability,
MultiQC, RNA-SeQC (per cellular barcode) and FastQC output.


## Input:

Cellular barcode list (see option `-c`): All samples barcodes must be
listed in this file (for non-demux use "1")

See `cfg/references.yaml` for reference data (reference genome, index,
annotation and gene id files) used by default (also refer to option
`--references-cfg`).

In addition you will need to provide sample definitions, either
through a config file (`--sample-cfg`) or through a full definition on
the commandline (options `-1`, `-2` and `-s`).

## Output:

The following lists the most important files/directories that are
created per sample in correspondingly named subfolders of `out`:

- `Results/gene_ExpressionMatrix.csv`: Expression matrix from STAR aligned BAM file
- `kallisto/kallisto.tagcount.txt`: Expression matrix by Kallisto
- `mb-histogram.txt`: Number of of raw reads from each cell barcode-UMI
- `cb-histogram.txt`: Number of of raw reads from each cell barcode

Reports:
- `Reports/FinalReport.html`: MultiQC output
- `Reports//QCreports/{sample}_fastqc.html`: FastQC output
- `Reports/SummarisedStats.csv`: Summary stats of reads preprocessing, STAR, featurecount, dedup logs etc.

## Notes

Deduplication can be very slow for large data-sets. If deduplication
 is not a must, we recommend to switch it off (`--no-dedup`).

## References

- scRNApipe: [website](https://github.com/MarinusVL/scRNApipe)
- umis: [website](https://github.com/vals/umis)
- Kallisto [website](https://pachterlab.github.io/kallisto/about) and [publication](https://www.ncbi.nlm.nih.gov/pubmed/27043002)
- Skewer: [publication](https://www.ncbi.nlm.nih.gov/pubmed/24925680) and [website](https://github.com/relipmoc/skewer)
