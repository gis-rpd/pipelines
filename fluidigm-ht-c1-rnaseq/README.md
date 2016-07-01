Description
-----------

This pipeline analyses RNA sequencing data from fluidigm single cell sequencing C1 mRNA Seq HT.

Following the bcl2fastq demultiplexing it uses fluidigm API script for demultiplexing the row barcodes (40) of column samples using R1 reads,
further only R2 reads are processed by prinseq-lite for poly (A) trimming and aligned to given reference genome using STAR mapper. 

Star aligner results list of files uniquely mapped genome bam, transcripts mapped bam which is used as an input for RSEM, gene based read count matix, wiggle files and mappability.
http://www.rna-seqblog.com/optimizing-rna-seq-mapping-with-star/

The transcripts/genes expression abundance were estimated by STAR and RSEM and exon level expression by DEXSeq.
RSEM results matrix  contains mapped reads count and TPM (normalized value) of genes and isoforms.

Other than bam and read count matrix this pipeline also provide deliverables such as stats, plots, coverage, mappability, QC, visualization files, etc.

The performance of STAR mapper in terms of speed and accuracy is better compared to other mappers for RNA seq data but it consume more memory.
some of the settings in star included from standard Encode options. Likewise RSEM makes accurate transcript quantification for RNA-seq data
compare to other methods such as HT-seq, feature counts.

Tools and methods used in the pipelines are Fluidigm API script, STAR, RSEM, samtools, DEXSeq, RNASeqQC.
RSEM - http://deweylab.github.io/RSEM/
STAR - https://github.com/alexdobin/STAR 
            https://groups.google.com/forum/#!forum/rna-star 
DEXSeq - http://bioconductor.org/packages/release/bioc/html/DEXSeq.html
http://www.ncbi.nlm.nih.gov/pmc/articles/PMC4728800/

All runtime variables including program versions etc. can be found in
`conf.yaml`


How to
------

- Run `fluidigm-ht-c1-rnaseq.py -h` to get basic usage information.
- If called correctly, jobs will be run on the cluster automatically
- Using `-v` is recommended to get some more information
- Should the pipeline 'crash', it can be restarted by simply running
  `bash run.sh` (for local mode) or `qsub run.sh` (for cluster mode).


Output
------

- The main log file is `./logs/snakemake.log`
- All output files can be found in `./out/`




