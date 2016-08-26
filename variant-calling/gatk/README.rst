Description
-----------

This pipeline implements the GATK best practices variant calling
workflow for single samples. If you are interested in more specialized
(e.g. cohort or trio) analyses, please reuse the gVCF file (or
realigned and recalibrated BAM file), also produced by this workflow.

Workflow settings are automatically changed according to the given sequencing
type, in particular 'base quality recalibration' (BQSR) and 'variant
quality recalibration' (VQSR) as explained in the following sections.

BQSR is skipped for targeted resequencing. For an explanation see
`this GAK article <http://gatkforums.broadinstitute.org/gatk/discussion/44/base-quality-score-recalibration-bqsr>`_,
or
`this GATK forum post <http://gatkforums.broadinstitute.org/gatk/discussion/4272/targeted-sequencing-appropriate-to-use-baserecalibrator-bqsr-on-150m-bases-over-small-intervals>`_.
Please note, that BAM file names do not indicate whether BQSR was actually run or not!


Hard variant filtering is always applied, following the recommendations in this
`this GATK howto <http://gatkforums.broadinstitute.org/gatk/discussion/2806/howto-apply-hard-filters-to-a-call-set>`_
and
`this GATK guide <https://www.broadinstitute.org/gatk/guide/article?id=3225>`_.
The corresponding variant files are called
``all_genotyped.snp_hfilter.vcf`` and ``all_genotyped.indel_hfilter.vcf``.
Note, it is recommended to optimize your filtering settings on a per
sample basis (which obviously cannot be part of any automated
workflow). 


For WGS sequencing only variant quality recalibration (VQSR) is also
run (for an explanation
see
`this GATK guide <https://www.broadinstitute.org/gatk/guide/article?id=3225>`_
and the
`section in the GATK best practices document <https://www.broadinstitute.org/gatk/guide/bp_step.php?p=2>`_).
The corresponding vcf files are called ``all_genotyped.snp_recal.vcf`` and ``all_genotyped.indel_recal.vcf``.

Note, VQSR can fail for perfectly valid reasons (e.g. too few uniq variants). In such cases
a fake vcf file will be produced which contains one line indicating
the problem. In such cases, resort to the hard filtered files.

Please also note, that the best practices do not recommend to use a
minimum depth filter and hence it's not used here either.


How to
------

- Run ``gatk.py -h`` to get basic usage information.
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
- Each read unit will have its own realigned, recalibrated BAM file, e.g. ``./out/unit-e5b71e98.bwamem.realn.recal.bam``
- Note that BQSR is skipped for targeted sequencing but the ``recal`` file name extension is maintained
- See ``conf.yaml`` for a defintion of readunits
- Raw genotype calls: ``./out/all_genotyped.vcf``
- gVCF: ``./out/<sample>.concat.gvcf``
- Hard-filtered snp/indel calls: ``./out/all_genotyped.<snp|indel>_hfilter.vcf``
- Recalibrated snp/indel calls (for WGS only): ``./out/all_genotyped.<snp|indel>_recal.vcf``
- Parameters including program versions etc. can be found in ``conf.yaml``





