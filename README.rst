# Pipelines developed by the Research Pipeline Development Team (RPD) for use in the Genome Institute of Singapore (GIS)


Using
[![Snakemake](https://img.shields.io/badge/snakemake-≥3.5.2-brightgreen.svg?style=flat-square)](http://snakemake.bitbucket.org)


## Setup Notes

- Create $RPD_ROOT/elm-logs.testing/${p} and $RPD_ROOT/elm-logs/${p} for p in pipelines (see `tools/create_pipeline_dirs.sh`)
- Install snakemake into its own conda env (see pipelines.py)
- Install pymongo into conda root env and snakemake env

