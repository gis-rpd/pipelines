Description
-----------

This pipeline implements the GATK best practices variant calling
workflow. Settings are adapted based on the given sequencing type.
In particular:
- Base quality recalibration (BQSR) is skipped for targeted resequencing. For an explanation see
  [thread 6894](http://gatkforums.broadinstitute.org/wdl/discussion/6894/gatk-best-practices-for-exome-targeted-capture-small-region)
  and
  [thread 4272](http://gatkforums.broadinstitute.org/gatk/discussion/4272/targeted-sequencing-appropriate-to-use-baserecalibrator-bqsr-on-150m-bases-over-small-intervals)
  in the BROAD forum.
- Note, that the file name does not indicate whether BQSR was actually run or not!
- Variant quality recalibration (VQSR) is skipped for targeted sequencing and exomes. For an explanation see
  [this document](https://www.broadinstitute.org/gatk/guide/article?id=3225) and the [section in the best practices document](https://www.broadinstitute.org/gatk/guide/bp_step.php?p=2)q
- Instead hard filtering is applied (as described
  [here](https://www.broadinstitute.org/gatk/guide/article?id=3225)). Note,
  it is actually recommend to optimize your filtering settings per
  sample sample. So this is not part of this workflow


All runtime variables can be found in `conf.yaml`


How to
------

- Run `variant-calling-gatk.py -h` to get basic usage information.
- Using -v is recommended to get some more information
- If called correctly, jobs will be run on the cluster automatically
- Should the pipeline 'crash' for technical reasons, it can be restarted by simply running
  `bash run.sh` (for local mode) or `qsub run.sh` (for cluster mode).
  Note that a crash due to input file or parameter issues can not be resolved in this fashion.
- All log files can be found in `./logs/`
- All output files can be found in `./out/`




