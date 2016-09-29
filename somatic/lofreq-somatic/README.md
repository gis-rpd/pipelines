# lofreq-somatic

## Summary

This pipeline calls somatic variants with [LoFreq Somatic](http://csb5.github.io/lofreq/).

The following steps are performed:

- Read mapping (see `cfg/references.yaml` for references used by default)
- Duplicate marking with samblaster (if not instructed otherwise)
- Realignment with `lofreq viterbi`
- Base quality recalibration with `Lacer` (Swaine Chen
  <<mailto:slchen@gis.a-star.edu.sg>>), unless sequencing type is  "targeted"
- Calling of somatic variants (SNVs and indels) with [LoFreq Somatic](http://csb5.github.io/lofreq/)

## Output

- Recalibrated BAM files for normal and tumor in the correspondly named subfolders
- VCF files produced by LoFreq Somatic can be found in the `variants` subfolder. The most important are
    - `lofreq_somatic_raw.{type}.vcf.gz`: Raw somatic variants
    - `lofreq_somatic_final.{type}.vcf.gz`: Final somatic variants
    - `lofreq_somatic_final_minus-dbsnp.{type}.vcf.gz`: Final somatic variants with dbSNP matches removed

