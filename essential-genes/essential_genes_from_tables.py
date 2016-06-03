#!/usr/bin/env python2
import sys
import os
import csv

from scipy.stats import hypergeom
from Bio import SeqIO


GB_FILE = "ref/Propionibacterium_acnes_NC_017550.genes.gbk"
# regions could be inferred from gb here, but were derived with snpeff
# so we parse both
BED_FILE = "ref/Propionibacterium_acnes_NC_017550.genes.bed"


def get_gene_lengths():
    """infer gene length from bed"""

    gene_lengths = dict()
    with open(BED_FILE) as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            _chrom, start, end, gene_name_and_id = line.rstrip().split("\t")
            gene_id = gene_name_and_id.split(";")[1]
            start, end = (int(x) for x in [start, end])
            gene_lengths[gene_id] = abs(end-start)
    return gene_lengths


def hypergeometric_test(x, M, n, N):
    """
    The hypergeometric distribution models drawing objects from a bin.
    - M is total number of objects
    - n is total number of Type I objects. 
    - x (random variate) represents the number of Type I objects in N drawn without replacement from the total population

    - http://en.wikipedia.org/wiki/Hypergeometric_distribution
    - https://www.biostars.org/p/66729/
    - http://docs.scipy.org/doc/scipy-0.14.0/reference/generated/scipy.stats.hypergeom.html
    - http://docs.scipy.org/doc/numpy/reference/generated/numpy.random.hypergeometric.html
    - http://stackoverflow.com/questions/6594840/what-are-equivalents-to-rs-phyper-function-in-python
    """

    assert n <= M
    assert x <= n
    assert N <= M
    pv_le = hypergeom.cdf(x+1, M, n, N)
    pv_gt = hypergeom.sf(x-1, M, n, N)# 1-cdf sometimes more accurate
    return pv_le, pv_gt
    

def parse_gene_id_and_name():
    """return a mapping of genes ids to gene names/description as dictionary
    
    deliberately only looking at protein coding genes
    """

    gene_id_to_name = dict()

    # modelled after http://genome.crg.es/~lpryszcz/scripts/gb2gtf.py
    #allowed_types = set(['gene', 'CDS', 'tRNA', 'tmRNA', 'rRNA', 'ncRNA'])
    allowed_types = set(['CDS'])
    #wanted_qualifiers = set(['product', 'locus_tag'])
    with open(GB_FILE) as fh:
        for gb in SeqIO.parse(fh, 'gb'):
            for f in gb.features:
                if f.type not in allowed_types:
                    continue
                qualifiers = dict(f.qualifiers)
                assert len(qualifiers['locus_tag'])==1 and len(qualifiers['product'])==1
                gene_id = qualifiers['locus_tag'][0]
                gene_name = qualifiers['product'][0]
                assert len(qualifiers['locus_tag']) == 1, (qualifiers['locus_tag'])
                gene_id_to_name[gene_id] = gene_name
    return gene_id_to_name



def main():
    """main function
    """
    
    # NOTES
    #1: sum(variants_impact_MODIFIER) - sum(variants_effect_downstream_gene_variant) - sum(variants_effect_upstream_gene_variant) == 0"
    # 2: normalizing variants_impact_MODIFIER not possible since overlapping with genes"
    # 3: adding variants_impact_HIGH into variants_impact_MODERATE"
    # 4: this is using the updated refseq annotation instead of kegg and therefore also no pathways"
    # all arguments are snpeff_genes_files
    #
    snpeff_genes_files = sys.argv[1:]
    for f in snpeff_genes_files:
        assert os.path.exists(f), (
            "Non-existing file {}".format(f))


    # load gene ids, names and lengths and check consistency

    gene_id_to_name = parse_gene_id_and_name()
    print "DEBUG: gene_id_to_name = {}...".format(gene_id_to_name.items()[:3])

    gene_lengths = get_gene_lengths()
    total_gene_len = float(sum(gene_lengths.values()))

    for g in gene_id_to_name.keys():
        assert g in gene_lengths.keys()
    # the reverse is not true because gene_id_to_name only contains CDS but bed contains all

    genes = set(gene_id_to_name.keys())


    # initialize gene_variant_counts for each variant category (VAR_COUNT_KEYS)
    #
    VAR_COUNT_KEYS = ['variants_impact_HIGH', 'variants_impact_MODERATE']#, 'variants_impact_MODIFIER']
    gene_variant_counts = dict()
    for g in genes:
        gene_variant_counts[g] = dict()
        for k in VAR_COUNT_KEYS:
            gene_variant_counts[g][k] = 0


    # read counts from list of snpeff gene files
    #
    for f in snpeff_genes_files:
        with open(f, 'r') as fh:
            _ = fh.next()# skip stupid "this is a csv file" line
            csvr = csv.DictReader(fh, delimiter='\t')
            for row in csvr:
                gene_id = row['GeneId']
                for k in VAR_COUNT_KEYS:
                    #print "DEBUG {}".format(row[k])
                    count = int(row[k])
                    gene_variant_counts[gene_id][k] = gene_variant_counts[gene_id].get(k, 0) + count

                
    # merge high into moderate counts because any high is also moderate
    #
    for g in gene_variant_counts.keys():
        gene_variant_counts[g]['variants_impact_MODERATE'] += gene_variant_counts[g].get('variants_impact_HIGH', 0)                


    total_gene_var_count = dict()
    for g in gene_variant_counts.keys():
        for v in VAR_COUNT_KEYS:
            count = gene_variant_counts[g][v]
            total_gene_var_count[v] = total_gene_var_count.get(v, 0) + count

    if True:
        num_genes = len(genes)
        print "#DEBUG: total_gene_len={}".format(total_gene_len)
        print "#DEBUG: num_genes={}".format(num_genes)
        for k, v in total_gene_var_count.items():
            print "#DEBUG: total_gene_var_count[{}]={}".format(k, v)


    print "#gene\timpact\tcounts\trel-len\tcorr pv_le\tcorr pv_gt\tdescription"
    for g in gene_variant_counts.keys():
        for v in VAR_COUNT_KEYS:#pathway_variant_counts[p].keys():
            counts = gene_variant_counts[g][v]
            pv_le, pv_gt = hypergeometric_test(
                counts,# type1 objects drawn from N
                total_gene_len, # total number of objects
                gene_lengths[g], # total number of type I objects
                total_gene_var_count[v] # N
                )
            pv_le *= len(gene_variant_counts.keys())
            pv_gt *= len(gene_variant_counts.keys())

            rel_len = gene_lengths[g]/float(total_gene_len)
            print "{}\t{}\t{}\t{}\t{}\t{}\t{}".format(
                g, v.replace("variants_impact_", ""), counts, rel_len,
                pv_le, pv_gt, gene_id_to_name[g])
    
    
if __name__ == "__main__":
    if len(sys.argv)<2:
        sys.stderr.write("FATAL: needs one more multiple snpEff_genes.txt files as input\n")
        sys.exit(1)
    main()
    sys.stderr.write("CRITICAL: needs usage info and fix for multiple testing corrections\n")

