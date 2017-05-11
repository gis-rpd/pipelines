#!/bin/bash -l
# need login shell for uge support


host=$1
test -z "$host" && exit 1

# disable all queues
qmod -d all.q@$host;

# force deletion of all jobs
for jid in $(qhost -j -h $host | awk '/MASTER/ {print $1}'); do
    qdel -f $jid;
done

# remove from executiom host list
qconf -de $host;
