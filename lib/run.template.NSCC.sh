#!/bin/bash

# Use the following to submit the workflow to the cluster:
#   qsub [-q queue] run.sh [>> log/submission.log]
# To run everythin locally use
#   bash run.sh
# To run the master process locally but submit worker jobs:
#   LOCAL_MASTER=1 bash run.sh
# For reruns, just run the same as above
#
# You can change the behaviour of this script through the following environment variables:
#
# - EXTRA_SNAKEMAKE_ARGS will be passed down to snakemake. This allows
#   for example to execute a dryrun: EXTRA_SNAKEMAKE_ARGS="--dryrun"
#   bash|qsub run.sh
#
# - SLAVE_Q: specify queue for the "worker processes" (otherwise
#   DEFAULT_SLAVE_Q set here will be used or scheduler decides if
#   empty)
#
# - DRMAA_OFF: disables DRMAA if set to 1
#
# - DEBUG: if set the snakemake command will be printed but not  exectuted
#
# - LOCAL_MASTER: run snakemaster locally and submit worker jobs

# PBS Pro options:
# The #PBS must be used to specify PBS Pro options
# declare a name for this job to be sample_job
#PBS -N {PIPELINE_NAME}.master
# logs
#PBS -o {LOGDIR}
# combine stdout/stderr
#PBS -j oe
# snakemake control job run time: 175h == 1 week
#PBS -l walltime={MASTER_WALLTIME_H}:00:00
# cpu & memory: memory can be high for complex DAGs and depends on local rules
#PBS -l select=1:mem=8g:ncpus=1
# keep env so that qsub works
#PBS -V
# Equivalent for SGE's -cwd doesn't exist in PBS Pro. See below for workaround
# Email address (for abort and kills only, everything else handled by snakemake)
#PBS -M {MAILTO}
#PBS -m a
#PBS -P 13000026

DEBUG=${{DEBUG:-0}}
RESTARTS=${{RESTARTS:-{DEFAULT_RESTARTS}}}
export DRMAA_LIBRARY_PATH=/app/pbs-drmaa/pbs_dramaa_fix/drmaa/lib/libdrmaa.so
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/app/pbs-drmaa/pbs_dramaa_fix/pbs_exec/lib:/app/pbs-drmaa/pbs_dramaa_fix/drmaa/lib
DRMAA_OFF=${{DRMAA_OFF:-1}}
LOCAL_CORES=${{LOCAL_CORES:-1}}
DEFAULT_SLAVE_Q={DEFAULT_SLAVE_Q}
LOCAL_MASTER=${{LOCAL_MASTER:-0}}
SNAKEFILE={SNAKEFILE}
LOGDIR="{LOGDIR}";# should be same as defined above
DEFAULT_SNAKEMAKE_ARGS="--local-cores $LOCAL_CORES --restart-times $RESTARTS --rerun-incomplete --timestamp --printshellcmds --stats $LOGDIR/snakemake.stats --configfile conf.yaml --latency-wait 60 --max-jobs-per-second 1 --max-status-checks-per-second 0.1 --keep-going"
# --rerun-incomplete: see https://groups.google.com/forum/#!topic/snakemake/fbQbnD8yYkQ
# --timestamp: prints timestamps in log
# --printshellcmds: also prints actual commands
# --latency-wait: might help with FS sync problems. also used by broad: https://github.com/broadinstitute/viral-ngs/blob/master/pipes/Broad_LSF/run-pipe.sh


if [ "$ENVIRONMENT" == "BATCH" ] || [ $LOCAL_MASTER -eq 1 ]; then
    # define qsub options for all jobs spawned by snakemake
    clustercmd="-l select=1:ncpus={{threads}}:mem={{cluster.mem}} -l walltime={{cluster.time}}"
    # log files names: qsub -o|-e: "If path is a directory, the standard error stream of
    clustercmd="$clustercmd -e $LOGDIR -o $LOGDIR"
    # PBS: cwd (workaround for missing SGE option "-cwd")
    test "$ENVIRONMENT" == "BATCH" && cd $PBS_O_WORKDIR
    if [ -n "$SLAVE_Q" ]; then
        clustercmd="$clustercmd -q $SLAVE_Q"
    elif [ -n "$DEFAULT_SLAVE_Q" ]; then 
        clustercmd="$clustercmd -q $DEFAULT_SLAVE_Q"
    fi
    # This is a crutch for inserting the SG10K project id (also used
    # in directive above).  Using -P with DRMAA fails with "DRMAA
    # Error: code 14: Invalid native specification:". Using the env
    # var is a valid workaround. FIXME make project part of site.yaml
    # and have a placeholder here. Shouldn't go on github!
    clustercmd="$clustercmd -v project=13000026"
    if [ "$DRMAA_OFF" -eq 1 ]; then
        #clustercmd="--cluster \"qsub $clustercmd\""
	    clustercmd="--cluster-sync \"qsub -Wblock=true $clustercmd\""
	    #clustercmd="--cluster-sync \"qsub -P 13000026 -Wblock=true $clustercmd\""
    else
        clustercmd="--drmaa \" $clustercmd\""
    fi
    CLUSTER_ARGS="--cluster-config cluster.yaml $clustercmd --jobname \"{PIPELINE_NAME}.slave.{{rulename}}.{{jobid}}.sh\""
    N_ARG="--jobs 25"
else
    # run locally
    CLUSTER_ARGS=""
    N_ARG="--cores 8"
fi


# snakemake setup
source rc/snakemake_init.rc || exit 1

test -d $LOGDIR || mkdir $LOGDIR


sm_args="-s $SNAKEFILE"
sm_args="$sm_args $N_ARG"
sm_args="$sm_args $DEFAULT_SNAKEMAKE_ARGS"
sm_args="$sm_args $EXTRA_SNAKEMAKE_ARGS"

# warn if we received any args from outside that match used ones
sm_args_tokenized=$(echo "$sm_args" | tr ' ' '\n' | grep '^-' | sort)
dups=$(echo -e "$sm_args_tokenized" | uniq -d)
if [[ $dups ]]; then
    echo "WARNING: duplicated args: $dups" 1>&2
fi

# now okay to add CLUSTER_ARGS (allows repeated -l)
sm_args="$sm_args $CLUSTER_ARGS"

# ANALYSIS_ID created here so that each run gets its own Id
# iso8601ms timestamp as corresponding python function
iso8601ns=$(date --iso-8601=ns | tr ':,' '-.');
iso8601ms=${{iso8601ns:0:26}}
ANALYSIS_ID=$iso8601ms
sm_args="$sm_args --config ANALYSIS_ID=$ANALYSIS_ID"


# mongodb update has to happen here because at this stage we know the
# job has been submitted. at the same time we avoid cases where a job
# stuck in queue will be rerun. but don't update if running in dryrun
# mode
is_dryrun=0
sm_args_tokenized=$(echo "$sm_args" | tr ' ' '\n' | grep '^-' | sort)
for arg in $sm_args_tokenized; do
    if [ $arg == "-n" ] || [ $arg == "--dryrun" ]; then
        is_dryrun=1
        break
    fi
done
if [ $is_dryrun != 1 ]; then
    {LOGGER_CMD}
else
    echo "Skipping MongoDB update (dryrun)"
fi


cmd="snakemake $sm_args >> {MASTERLOG} 2>&1"
if [ $DEBUG -eq 1 ]; then
    echo $cmd
else
    if [ $LOCAL_MASTER -eq 1 ]; then
	eval nohup $cmd &>> $LOGDIR/local_master.log &
    else
	eval $cmd
    fi
fi
