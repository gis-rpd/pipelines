#!/bin/bash -l
# need login shell for uge support

set -u

WATCHDIR=/scratch/spot_termination_notices/

for f in $(find $WATCHDIR/ -name \*.log); do
    host=$(cat $f | cut -f 1)
    termtime=$(cat $f | cut -f 2)

    echo "Removing host $host with termination time $termtime from UGE"

    # disable all queues
    echo "...disabling queues for host $host"
    qmod -d all.q@$host;

    # force deletion of all jobs
    echo "...deleting jobs"
    for jid in $(qhost -j -h $host | awk '/MASTER/ {print $1}'); do
	qdel -f $jid;
    done

    # delete the host
    echo "...deleting host"
    qconf -de $host;

     # this assumes the file will not be created again while waiting for termination
    mv $f ${f%.log}.handled
done

