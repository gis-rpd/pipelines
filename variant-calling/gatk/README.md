# gatk


## Summary

This pipeline implements the GATK best practices variant calling
workflow (v3.6) for single samples. It's major output are a
recalibrated BAM file, genotyped gVCF and VCF files (per sample). 

See `cfg/references.yaml` for references used by default (also refer
to option `--references-cfg`)

If you are interested in more specialized analyses (e.g. cohort or
trio), please reuse the gVCF file (or recalibrated BAM file) produced
by this workflow.

Settings are automatically changed according to the given sequencing
type, in particular 'base quality recalibration' (BQSR) and 'variant
quality recalibration' (VQSR) as explained in the following sections.

BQSR is skipped for targeted resequencing. For an explanation see
[this GAK article](http://gatkforums.broadinstitute.org/gatk/discussion/44/base-quality-score-recalibration-bqsr>),
or
[this GATK forum post](http://gatkforums.broadinstitute.org/gatk/discussion/4272/targeted-sequencing-appropriate-to-use-baserecalibrator-bqsr-on-150m-bases-over-small-intervals).
Please note, that BAM file names do not indicate whether BQSR was actually run or not!

Variant quality recalibration (VQSR) is run only for WGS data.  The
corresponding vcf files are called `all_genotyped.snp_recal.vcf` and
`all_genotyped.indel_recal.vcf`. The reason is explained here:
[Which training sets / arguments should I use for running VQSR?](https://software.broadinstitute.org/gatk/guide/article?id=1259)
(last updated 2016-08-30):

> in order to achieve the best exome results one needs to use an 
> exome SNP and/or indel callset with at least 30 samples.

Note, VQSR can fail for perfectly valid reasons (e.g. too few uniq
variants). In such cases a fake vcf file will be produced which
contains one line indicating the problem. In such cases, resort to the
hard filtered files.

Hard variant filtering is always applied, following the recommendations in this
[this GATK howto](http://gatkforums.broadinstitute.org/gatk/discussion/2806/howto-apply-hard-filters-to-a-call-set)
and
[this GATK guide](https://www.broadinstitute.org/gatk/guide/article?id=3225).
The corresponding variant files are called
`all_genotyped.snp_hfilter.vcf` and `all_genotyped.indel_hfilter.vcf`.
Note, it is recommended to optimize your filtering settings on a per
sample basis (which obviously cannot be part of any automated
workflow). 

## Output

- Each "readunit" will have its own realigned, recalibrated BAM file, e.g. `{unit}.bwamem.realn.recal.bam`. See `conf.yaml` for a description of units
- Note that BQSR is skipped for targeted sequencing but the `recal` file name extension is maintained
- Raw genotype calls: `all_genotyped.vcf`
- gVCF: `{sample}.concat.gvcf`
- Hard-filtered snp/indel calls: `all_genotyped.{type}_hfilter.vcf`
- Recalibrated snp/indel calls (for WGS only): `all_genotyped.{type}_recal.vcf`


## References


- [Call variants with HaplotypeCaller](https://software.broadinstitute.org/gatk/documentation/article?id=2803) (last updated 2016-02-11)
- [Recalibrate variant quality scores = run VQSR](https://software.broadinstitute.org/gatk/documentation/article?id=2805) (last updated 2014-12-17)
- [Apply hard filters to a call set](https://software.broadinstitute.org/gatk/documentation/article?id=2806) (last updated 2016-07-28)

