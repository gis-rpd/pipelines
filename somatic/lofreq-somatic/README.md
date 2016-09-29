# lofreq-somatic

## Summary

This pipeline calls somatic variants with [LoFreq Somatic](http://csb5.github.io/lofreq/).

The following steps are performed:

- Read mapping (see `cfg/references.yaml` for references used by default and also refer to  option `--references-cfg`)
- Duplicate marking with samblaster (if not instructed otherwise)
- Realignment with `lofreq viterbi`
- Base quality recalibration with `Lacer` (Swaine Chen
  <<mailto:slchen@gis.a-star.edu.sg>>), unless sequencing type is  "targeted"
- Calling of variants (SNVs and indels) with [LoFreq](http://csb5.github.io/lofreq/)

## Output

- Recalibrated BAM file per sample: `{sample}.bwamem.lofreq.lacer.bam`
- Called variants: `{sample}.bwamem.lofreq.lacer.{type}.vcf.gz`
- Mapping statistics: `{sample}.bwamem.lofreq.lacer.bamstats`
