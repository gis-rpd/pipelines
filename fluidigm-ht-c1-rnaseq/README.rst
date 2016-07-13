Description
-----------

This pipeline analyses RNA sequencing data from `fluidigm single cell
sequencing C1 mRNA Seq HT
<https://www.fluidigm.com/c1openapp/scripthub/script/2015-08/mrna-seq-ht-1440105180550-2>`_.

Following conventional bcl2fastq demultiplexing it uses fluidigm API
script for demultiplexing the row barcodes (N=40) of column samples
using R1 reads. Subsequently R2 reads are poly-A trimmed
(with `prinseq-lite <http://prinseq.sourceforge.net/>`_) and aligned to
given reference genome using the `STAR mapper
<https://github.com/alexdobin/STAR>`_. Output of STAR is the uniquely
mapped genome bam file, transcripts mapped bam file, gene based read
count matrix, wiggle files and mappability. For running STAR we follow
recipes given at
http://www.rna-seqblog.com/optimizing-rna-seq-mapping-with-star/

The transcripts/genes expression abundance are estimated by STAR and
`RSEM <//deweylab.github.io/RSEM/>`_ (reusing STAR's BAM file). The RSEM results matrix contains mapped reads count and TPM
(normalized value) of genes and isoforms. The pipeline also provides
generic stats, coverage, mappability, QC e.g. by running `RNA-SeQC <https://www.broadinstitute.org/cancer/cga/rna-seqc>`_.



How to
------

- Run ``fluidigm-ht-c1-rnaseq.py -h`` to get basic usage information.
- If called correctly, jobs will be run on the cluster automatically
- Using ``-v`` is recommended to get some more information
- Should the pipeline 'crash', it can be restarted by simply running
  ``bash run.sh`` (for local mode) or ``qsub run.sh`` (for cluster
  mode).  Note that a crash due to input file or parameter issues can
  not be resolved in this fashion.


Output
------

- The main log file is ``./logs/snakemake.log``
- After a successful run the last line in the snakemake log file will say ``(100%) done``
- All output files can be found in ``./out/``
- Furthermore a simple report have been generated (``./out/report.html``)
- Parameters including program versions etc. can be found in ``conf.yaml``

  
STAR:
`````

- Mapped genome BAM: <sample>_<genome>_Aligned.sortedByCoord.out.bam
- Mapped transcriptome BAM (RSEM input): <sample>_<genome>_Aligned.toTranscriptome.out.bam
- Visualization: Wiggle file (\*.wig)
- Read count (genes): <sample>_<genome>_ReadsPerGene.out.tab
- Mappability: <sample>_<genome>_Log.final.out

RSEM:
`````

- Genes expression values with annotation: <sample>_<genome>_RSEM.genes.results
- Isoforms expression values with annotation: <sample>_<genome>_RSEM.isoforms.results
- Visualization: .wig
- Plots: <sample>_<genome>_RSEM.pdf

RNA-SeQC:
`````````

QC and rate of rRNA and distribution of reads on transcripts:

- countMetrics.html
- metrics.tsv



