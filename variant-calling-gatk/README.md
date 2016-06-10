Description
-----------

This pipeline implements the GATK best practices variant calling
workflow.

Settings are adapted based on the given sequencing type, in particular
Base quality recalibration (BQSR) and Variant quality recalibration
(VQSR),


BQSR is skipped for targeted resequencing. For an explanation see
[this GAK article](http://gatkforums.broadinstitute.org/gatk/discussion/44/base-quality-score-recalibration-bqsr),
or [this GATK forum post](http://gatkforums.broadinstitute.org/gatk/discussion/4272/targeted-sequencing-appropriate-to-use-baserecalibrator-bqsr-on-150m-bases-over-small-intervals).

Please note, that the file name does not indicate whether BQSR was actually run or not!

Variant quality recalibration (VQSR) is skipped for targeted
sequencing and exomes. For an explanation see
[this GATK guide](https://www.broadinstitute.org/gatk/guide/article?id=3225)
and the
[section in the best practices document](https://www.broadinstitute.org/gatk/guide/bp_step.php?p=2). Instead
hard filtering is applied (as described
[in this guide](https://www.broadinstitute.org/gatk/guide/article?id=3225)). Note,
it is actually recommended to optimize your filtering settings on a per
sample basis (which obviously cannot be part of any automated workflow).

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




