#!/bin/bash

set -u

WATCHDIR=/scratch/spot_termination_notices/

for f in $(find $WATCHDIR/ -name \*.log); do
    host=$(cat $f | cut -f 1)
    termtime=$(cat $f | cut -f 2)

    msg="Removing host $host with termination time $termtime from UGE"
    logger -s -t $(basename $0) "$msg"

    $(dirname $0)/kill_uge_host.sh $host

     # this assumes the file will not be created again while waiting for termination
    mv $f ${f%.log}.handled
done

