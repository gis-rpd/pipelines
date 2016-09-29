# mutect

## Summary

This pipeline calls somatic variants with Mutect (version 1; see
[paper](http://www.nature.com/nbt/journal/v31/n3/abs/nbt.2514.html)
and [homepage](http://archive.broadinstitute.org/cancer/cga/mutect))


The following steps are performed:

- Read mapping (see `cfg/references.yaml` for references used by default)
- Duplicate marking with samblaster (if not instructed otherwise)
- Indel Realignment with GATK (targets inferred from normal and tumor samples)
- Base quality recalibration with `GATK`, unless sequencing type is "targeted"
- Calling of somatic variants with Mutect. By default a contamination level of 2% is used.


## Output

- Recalibrated BAM files for normal and tumor in the correspondly named subfolders
- Mutect results can be found in the `variants` subfolder. The most important are
    - `mutect.txt.gz`: Mutect's extended output
    - `mutect.wig.gz`: Coverage data
    - `mutect.vcf.gz`: All variants
    - `mutect.PASS.vcf.gz`: Only passed variants


