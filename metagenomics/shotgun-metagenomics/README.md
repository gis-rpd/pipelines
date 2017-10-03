# shotgun-metagenomics

## Summary

This pipeline analyses paired-end shotgun metagenomics data. In a
first step is trims adapters and low-quality bases by using
Skewer. Reads are then decontaminated against reference specified in
the config file (default: human). Then, several metagenomics profilers
(default: Kraken and Metaphlan2) and a pathway analysis with HUMAnN2
is performed. Results aggregated over all input samples. In addition
resistance gene typing results are produced with SRST2.

This pipeline was originally developed by
[Chenhao Li](https://github.com/orgs/CSB5/people/lch14forever) (see
[Github repository](https://github.com/CSB5/shotgun-metagenomics-pipeline)). The
SRST2 logic was added by KOH Jia Yu (Jayce).


## Output

The following lists the main output files

- `{sample}/reads/all-trimmed-decont_[12].fastq.gz` is the (if
 needed concatenated,) quality trimmed and decontaminated read pair
- `{sample}/reads/counts.txt`: read counts after trimming and after
 decontamination
- `{sample}/srst2/{sample}__genes__{db}__results.txt` and  `{sample}/srst2/{sample}__fullgenes__{db}__results.txt`: SRST2
   resistance gene typing results (see
  [SRST2 documentation](https://github.com/katholt/srst2#gene-typing))
- `merged_table_{profiler}/{tax}.{profiler}.profile_merged.tsv` where
  `profiler` can be `kraken` or `metaphlan2` and `tax` is a one-letter
  abbreviation for taxonomic rank (e.g. `g` for genus). Please note
  that Metaphlan2 lists abundances as percentage, whereas Kraken
  produces read counts
- `merged_table_humann2/genefamily.tsv`: Abundance (in RPK) of each
  gene family (each row) in each sample (each column)
- `merged_table_humann2/pathabundance.tsv`: Abundance of each pathway
  in each sample. The pathways are stratified into species.
- `merged_table_humann2/pathcoverage.tsv`: Presence (1)/absence (0)
  code for each pathway in each sample.


## References

- Skewer: [Publication](https://www.ncbi.nlm.nih.gov/pubmed/24925680) and [website](https://github.com/relipmoc/skewer)
- Kraken: [Publication](https://genomebiology.biomedcentral.com/articles/10.1186/gb-2014-15-3-r46) and [website](https://ccb.jhu.edu/software/kraken/)
- Metaphlan2: [Publication](https://www.nature.com/nmeth/journal/v12/n10/full/nmeth.3589.html) and [website](http://segatalab.cibio.unitn.it/tools/metaphlan2/)
- HUMAnN2: [Website](http://huttenhower.sph.harvard.edu/humann2)
- Decont: [Website](https://github.com/CSB5/decont)
