#!/bin/bash
computenodes=$(qhost | sed -e '1,3d' | cut -f 1 -d ' ')
for host in $computenodes; do 
  # check if alive
  ping -q -c 3 $host >/dev/null && continue; 
  echo $host not okay;  

  # disable all queues
  qmod -d all.q@$host;
  # force deletion of all jobs
  for jid in $(qhost -j -h $host | awk '/MASTER/ {print $1}'); do 
    qdel -f $jid; 
  done
  # delete the host
  qconf -de $host
done

