Description
-----------

This pipeline is for RNASeq bulk analysis and runs STAR, followed by
RNASeQC, RSEM and optionally cuffdiff. It's most suitable for 
all types of RNASeq except small RNASeq.

Reads are aligned to given reference genome using the STAR mapper. Output of
STAR is the uniquely mapped genome bam file, transcripts mapped bam
file (used as input for RSEM), gene based read count matrix, wiggle
files and mappability. For running STAR we follow recipes given at
http://www.rna-seqblog.com/optimizing-rna-seq-mapping-with-star/

https://groups.google.com/forum/#!topic/rna-star/gZRJx3ElRNo

The transcripts/genes expression abundance are estimated by STAR and
RSEM. The RSEM results matrix contains mapped reads count and TPM
(normalized value) of genes and isoforms. The pipeline also provides
generic stats, coverage, mappability, QC and other analysis. 

The cuffdiff method is slow compare to default method, actually it 
runs in cufflinks mode with no differential analysis carried out to get 
raw fragment count of genes and isoforms in addition to cufflinks fpkm. 
By this method the pipeline supports strand specific analysis if the 
library type is "fr-firststrand" by default "fr-unstranded ".

 http://www.nature.com/nprot/journal/v7/n3/fig_tab/nprot.2012.016_T1.html

 http://onetipperday.sterding.com/2012/07/how-to-tell-which-library-type-to-use.html

The expression values of genes and isoforms are provided with annotation 
in all the methods.

- RSEM: http://deweylab.github.io/RSEM/
- STAR: https://github.com/alexdobin/STAR 
- RNA-SeQC: https://www.broadinstitute.org/cancer/cga/rna-seqc
- CUFFDIFF: http://cole-trapnell-lab.github.io/cufflinks/manual/

Note that STAR is very memory hungry. We use its shared memory option
with the goal of reducing the memory burden. However, with many jobs
running on the cluster, loading and unloading of genome indices on the
same node can lead to race conditions. In such cases workflow will
fail, but can simply be rerun (see below). Worst case is shared memory
not being freed on nodes. In such cases (run ``ipcs`` to find out) manual
unloading (``STAR --genomeLoad Remove`` or ``ipcrm -M``)




How to
------

- Run ``rnaseq-bulk.py -h`` to get basic usage information.
- If called correctly, jobs will be run on the cluster automatically
- Using ``-v`` is recommended to get some more information
- Should the pipeline 'crash', it can be restarted by simply running
  ``bash run.sh`` (for local mode) or ``qsub run.sh`` (for cluster mode).


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
- Read count (genes): <sample>_<genome>_ReadsPerGene.out.tab.desc
- Mappability: <sample>_<genome>_Log.final.out

RSEM:
`````

- Genes expression values with annotation: <sample>_<genome>_RSEM.genes.results.desc
- Isoforms expression values with annotation: <sample>_<genome>_RSEM.isoforms.results.desc
- Visualization: .wig
- Plots: <sample>_<genome>_RSEM.pdf

RNA-SeQC:
`````````

QC and rate of rRNA and distribution of reads on transcripts:

- countMetrics.html
- metrics.tsv

Cuffdiff:
`````````

- Genes expression values with annotation: <sample>_<genome>_genes_FPKM_Rawreadcount_GIS.txt
