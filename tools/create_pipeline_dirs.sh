#!/bin/bash

pipelines=$@
test -z "$pipelines" && exit 1

# elm logging dirs
#
for suf in "" ".testing"; do
  for p in $pipelines; do
    d=$(echo $RPD_ELMLOGDIR | sed -e 's,/$,,')${suf}/${p}
    echo "Creating $d (if needed) and setting perms as required"
#cat<<EOF
    test -d $d || mkdir -p $d 2>/dev/null
    chmod 777 $d
    chmod g+s $d
#EOF
  done
done

# downstream dirs
#
for d in $(grep -A2 downstream_outdir_base etc/site.yaml  | awk '/(devel|production):/ {print $NF}'); do
    # next level is user. so only need to be sure this toplevel is writeable
    echo "Creating $d (if needed) and setting perms as required"
    test -d $d || mkdir -p $d 2>/dev/null
    chmod 775 $d
    chmod g+s $d
done
