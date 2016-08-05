# Setup Notes

**NOTE**: this setup is of limited use without auxiliary components
i.e. our specialized MongoDB setup used for logging and tracking


- Create a snakemake environment with needed components:
  - `conda create -n snakemake-3.7.1 pymongo drmaa python-dateutil`
  - `conda install -n snakemake-3.7.1 snakemake=3.7.1 -c bioconda`
  - Change `lib/pipelines.py:write_snakemake_init` to point to this env
- Install other components into conda root env: 
  - `conda install pymongo drmaa yaml pylint python-dateutil`
- Install pymongo into conda root env
- Create testing and logging directories per pipeline (see `tools/create_pipeline_dirs.sh`)
- Software/modules management is based on dotkit. See also `lib/pipelines.py:INIT`
- Test scripts expect `RPD_ROOT` to be set
- ELM logging goes to `RPD_ELMLOGDIR`

