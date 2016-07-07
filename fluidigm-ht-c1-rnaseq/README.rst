Description
-----------

This pipeline analyses RNA sequencing data from `fluidigm single cell
sequencing C1 mRNA Seq HT
<https://www.fluidigm.com/c1openapp/scripthub/script/2015-08/mrna-seq-ht-1440105180550-2>`_.

Following the bcl2fastq demultiplexing it uses fluidigm API script for
demultiplexing the row barcodes (N=40) of column samples using R1
reads. Subsequently R2 reads are poly-A trimmed (prinseq-lite) and
aligned to given reference genome using the STAR mapper. Output of
STAR is the uniquely mapped genome bam file, transcripts mapped bam
file (used as input for RSEM), gene based read count matrix, wiggle
files and mappability.  See
http://www.rna-seqblog.com/optimizing-rna-seq-mapping-with-star/

The transcripts/genes expression abundance are estimated by STAR and
RSEM. The RSEM results matrix contains mapped reads count and TPM
(normalized value) of genes and isoforms.

The pipeline also provides generic stats, coverage, mappability, QC
and other analysis.

Tools and methods used in the pipelines are Fluidigm API script, STAR,
RSEM and RNASeqQC amongst others:
- RSEM: http://deweylab.github.io/RSEM/
- STAR: https://github.com/alexdobin/STAR 
- RNA-SeQC: https://www.broadinstitute.org/cancer/cga/rna-seqc

Deliverables::
star:
mapped genome bam - <library>_<assembly>_Aligned.sortedByCoord.out.bam
mapped transcriptome bam (required to run RSEM) - <library>_<assembly>_Aligned.toTranscriptome.out.bam
visualization - .wig
Read count (genes) - <library>_<assembly>_ReadsPerGene.out.tab
Mappability - <library>_<assembly>_Log.final.out
rsem:
genes expression values with annotation - <library>_<assembly>_RSEM.genes.results
isoforms expression values with annotation - <library>_<assembly>_RSEM.isoforms.results
visualization - .wig
plots - <library>_<assembly>_RSEM.pdf
rnaseqQC:
qc and rate of rRNA and distribution of reads on transcripts 
-countMetrics.html
-metrics.tsv

All runtime variables including program versions etc. can be found in
``conf.yaml``


How to
------

- Run ``fluidigm-ht-c1-rnaseq.py -h`` to get basic usage information.
- If called correctly, jobs will be run on the cluster automatically
- Using ``-v`` is recommended to get some more information
- Should the pipeline 'crash', it can be restarted by simply running
  ``bash run.sh`` (for local mode) or ``qsub run.sh`` (for cluster mode).


Output
------

- The main log file is ``./logs/snakemake.log``
- All output files can be found in ``./out/``




