# star-rsem

## Summary

This pipeline is for RNASeq analysis and runs STAR, followed by
RNASeQC, RSEM and optionally cuffdiff. It should be suitable for all
types of RNASeq, except small RNASeq.

Reads are aligned to given reference genome using the
[STAR mapper](https://github.com/alexdobin/STAR).  See
`cfg/references.yaml` for references used by default (also refer to
option `--references-cfg`).  Output of STAR includes the uniquely
mapped genome bam file, transcripts mapped bam file, gene based read
count matrix, bigwig files etc. (see below). For running STAR we
follow recipes given
[here](http://www.rna-seqblog.com/optimizing-rna-seq-mapping-with-star/).
 
The transcripts/genes expression abundance are estimated by STAR and
[RSEM](http://deweylab.github.io/RSEM/) (reusing STAR's BAM file). The
RSEM results matrix contains mapped reads count and TPM (normalized
value) of genes and isoforms. 

The pipeline also provides generic stats, coverage, mappability, QC
e.g. by running [RNA-SeQC](https://www.broadinstitute.org/cancer/cga/rna-seqc).

Cuffdiff can be run optionally (slow!): it will run in cufflinks mode,
with no differential analysis carried out, to get raw fragment count
of genes and isoforms in addition to cufflinks fpkm. If the `stranded`
option was used cuffdiff is run with `fr-firststrand`, otherwise
`fr-unstranded` by default

Expression values of genes and isoforms are provided with annotation 
in all run methods.


Note, STAR is very memory hungry. Because its shared memory option can
cause trouble when jobs fail (memory needs to be cleared manually), we
do not make use of it, even in a multi-sample setting.


  
## Output

The following lists the most important files/directories that are
created in correspondingly named subfolders:
  

### STAR

- Mapped genome BAM: `{sample}_{genome}_Aligned.sortedByCoord.out.bam`
- Mapped transcriptome BAM (RSEM input): `{sample}_{genome}_Aligned.toTranscriptome.out.bam`
- Visualization: Bigwig files (`*.bw`)
- Read count (genes): `{sample}_{genome}_ReadsPerGene.out.tab`
- Mappability stats: `{sample}_{genome}_Log.final.out`

Exact STAR mapping parameters can be looked up in the Snakefile.

### RSEM

- Genes expression values with annotation: `{sample}_{genome}_RSEM.genes.results.desc`
- Isoforms expression values with annotation: `{sample}_{genome}_RSEM.isoforms.results.desc`
- Visualization: Wiggle files (`*.wig`)
- Plots: `{sample}_{genome}_RSEM.pdf`

### RNA-SeQC


QC and rate of rRNA and distribution of reads on transcripts:

- `countMetrics.html`
- `metrics.tsv`


### Cuffdiff


- Genes expression values with annotation: `{sample}_{genome}_genes_FPKM_Rawreadcount_GIS.txt`
- Genes with raw fragment and fpkm value: `genes.read_group_tracking`
