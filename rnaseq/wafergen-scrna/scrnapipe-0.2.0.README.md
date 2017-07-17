# Installation of many required programs is anything but straightforward. For scrnapipe-0.2.0 we used the following

conda create -n scrnapipe-0.2.0 umis umi_tools STAR subread fastqc multiqc

wget -nd https://github.com/MarinusVL/scRNApipe/archive/v0.2.0.tar.gz
source activate scrnapipe-0.2.0
python setup.py install
conda install -n scrnapipe-0.2.0 natsort# mssing dep in scrnapipe-0.2.0

# Deal with pysam libbz2 problem by downgrading
# $ scRNApipe out/RHH5647/scrna.conf
# from pysam.libchtslib import *
# ImportError: libbz2.so.1.0: cannot open shared object file: No such file or directory
# $ conda list -n scrnapipe-0.2.0 -e | grep pysam
# pysam=0.11.2.2=htslib1.5_2
# $ conda list -n umis -e | grep pysam
# pysam=0.11.2.1=py27_0
# Therefore:
conda install -n scrnapipe-0.2.0 pysam=0.11.2.1=py27_0

# Run `umi_tools dedup` once as admin to build modules (network!). See https://github.com/CGATOxford/UMI-tools/issues/126
umi_tools dedup

