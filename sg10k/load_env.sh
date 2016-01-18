# UGE setup (as in /etc/profile)
#
echo "Setting up UGE"
export SGE_ROOT=/opt/uge-8.1.7p3
export SGE_CELL=aquila_cell
source $SGE_ROOT/$SGE_CELL/common/settings.sh


# dotkit
eval `/mnt/projects/rpd/init -b`


# load fixed snakemake version
#
echo "Activating snakemake"
#module load miniconda
use miniconda-3
#export PATH=/mnt/projects/rpd/apps/miniconda3/bin/:$PATH
source activate snakemake-3.5.4;


# load dotkits dependencies defined in conf.yaml
# FIXME rewrite properly as external script
for dk in $(python3 -c 'import yaml; f=open("conf.yaml"); print("\n".join(["{}-{}".format(k,v) for k, v in yaml.safe_load(f)["modules"].items()])); f.close()'); do
    use $dk
done
