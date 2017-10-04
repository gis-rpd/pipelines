# ChIPseq

## Summary

This pipeline calls peaks in ChIP-Seq data with
[MACS2](https://github.com/taoliu/MACS) and
[DFilter](http://collaborations.gis.a-star.edu.sg/~cmb6/kumarv1/dfilter/)
and performs motif discovery with [MEME-ChIP](http://meme-suite.org/).


The following steps are performed:

- Read mapping with BWA aln by default. See `cfg/references.yaml` for
  default references and also refer to option `--references-cfg`
- Filtering of duplicated, unmapped reads and reads with bad mapping
  quality (Q20).
- By default the pipeline will call peaks with both, MACS and
  DFilter. This behaviour can be changed with "--skip-macs2" and
  "--skip-dfilter".
- Extraction of sequences around extended peak regions followed by
  motif discovery with MEME-ChIP

Note, running a ChIPseq analysis requires a control and treatment
sample. When using a sample config as input (`--sample-cfg` or `-S`),
make sure that the control is named `control`.


## Peak Types

The peak type is library dependent and can be set with `--peak-type`
or `-t`. If set to `TF` or `histone-narrow`, MACS2 will call "narrow
peaks" in either case and DFilter options will be adjusted accordingly
If set to `histone-broad`, MACS2 will call "broad peaks" and "narrow
peaks" and DFilter options will be adjusted accordingly.  See the
DFilter
[tutorial](http://collaborations.gis.a-star.edu.sg/~cmb6/kumarv1/dfilter/tutorial.html#parameters)
for an explanation of options.

## Output

Processed BAM files (`*.bwa-aln-nsrt.bam`) for control and treatment
samples can be found in the correspondingly named subfolders in
`./out/`.

Peak calling results, motif discovery results and mapping stats can be
found in the `./out/treatment` subfolders. The most important are
- `treatment_peaks.xls`: Called peaks and peaks coordinates (MACS2
  only)
- `treatment.Peaks`: Called peaks and peaks coordinates (DFilter only)
- `treatment_summits.bed`: Peak summit locations for every peak
- `treatment_control_lambda.bw`: Control tag density profile
- `treatment_treat_pileup.bw`: Treatment tag density profile
- `treatment_filtered_treatment.wig`: Background smoothened treatment
  tag density profile (DFilter only)
- `treatment-memechip/index.html`: Motif discovery results
- `treatment.bwa-aln-nsrt.bamstats/stats.txt`: Mapping stats


