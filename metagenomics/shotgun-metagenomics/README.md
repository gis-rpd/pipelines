# shotgun-metagenomics


## Summary

This pipeline analyses paired-end shotgun metagenomics data. In a
first step is trims adapters and low-quality bases by using
Skewer. Reads are then decontaminated against reference specified in
the config file (default: human). Then, several metagenomics profilers
(default: Kraken and Metaphlan2) and a pathway analysis with HUMAnN2
is performed. Results aggregated over all input samples.

This pipeline was originally developed by
[Chenhao Li](https://github.com/orgs/CSB5/people/lch14forever) (see
[Github repository](https://github.com/CSB5/shotgun-metagenomics-pipeline)).

## Output

The following list the main output files

- `merged_table_{profiler}/{tax}.{profiler}.profile_merged.tsv` where
  `profiler` can be `kraken` or `metaphlan2` and `tax` is a one-letter
  abbreviation for taxonomic rank (e.g. `g` for genus).
- `merged_table_humann2/pathcoverage.tsv`: FIXME Add description (HUMAnN2 pathway analysis)
- `merged_table_humann2/genefamily.tsv`: FIXME Add description (HUMAnN2 pathway analysis)
- `merged_table_humann2/pathabundance.tsv`: FIXME Add description (HUMAnN2 pathway analysis)


## References

- Skewer: [Publication](https://www.ncbi.nlm.nih.gov/pubmed/24925680) and [website](https://github.com/relipmoc/skewer)
- Kraken: [Publication](https://genomebiology.biomedcentral.com/articles/10.1186/gb-2014-15-3-r46) and [website](https://ccb.jhu.edu/software/kraken/)
- Metaphlan2: [Publication](https://www.nature.com/nmeth/journal/v12/n10/full/nmeth.3589.html) and [website](http://segatalab.cibio.unitn.it/tools/metaphlan2/)
- HUMAnN2: [Website](http://huttenhower.sph.harvard.edu/humann2)
- Decont: [Website](https://github.com/CSB5/decont)
