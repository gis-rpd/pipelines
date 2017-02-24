#!/bin/bash -l
# need login shell for uge support

set -u


for host in $(qhost | awk 'NR>3 {print $1}'); do 
    ping -c 10 $host >/dev/null || continue;
    msg="Removing non pingeable host $host from UGE"
    logger -s -t $(basename $0) "$msg"

    $(dirname $0)/kill_uge_host.sh $host
done

