#!/bin/bash

set -eou pipefail

which bcftools > /dev/null || exit 1


usage() {
    myname=$(basename $(readlink -f $0))
    echo "$myname: very quick and very dirty PPV and sensitivity computation from vcf comparison "
    echo "usage: $myname -t truth.vcf -p prediction.vcf -T snps|indels [-S sens threshhold (0-1)] [-P ppv-threshold (0-1)]"
}
sens_thresh=0
ppv_thresh=0
truth=""
pred=""
vartype=""
while getopts ":t:p:S:P:T:h" opt; do
    case $opt in
        t)
            truth=$OPTARG;;
        p)
            pred=$OPTARG;;
        S)
            sens_thresh=$OPTARG;;
        P)
            ppv_thresh=$OPTARG;;
        T)
            vartype=$OPTARG;;
        h)
            usage; exit 0;;
        \?)
            echo "Invalid option: -$OPTARG" >&2;;
    esac
done

if [ -z "$truth" ] || [ ! -e "$truth" ]; then
    echo "ERROR: truth missing" 1>&2
    usage
    exit 1
fi
if [ -z "$pred" ] || [ ! -e "$pred" ]; then
    echo "ERROR: prediction missing" 1>&2
    usage
    exit 1
fi
if [ -z "$vartype" ]; then
    vartype_arg=""
else
    vartype_arg="-i 'TYPE=\"$vartype\"'"
fi

d=$(mktemp -d)
#cat<<EOF
eval bcftools isec $vartype_arg -n =2 -p $d $truth $pred 2>>$d/bcftools.log || exit 1
#EOF
#echo "debug exit" 1>&2; exit 1
tp=$(cat $d/sites.txt | wc -l)
p=$(eval bcftools view $vartype_arg $truth 2>>$d/bcftools.log | grep -vc '^#') || exit 1
sens=$(echo "scale=3; $tp/$p" | bc -l)
#echo "DEBUG tp=$tp p=$p" 1>&2
rm -rf $d
#echo "Keeping $d" 1>&2

d=$(mktemp -d)
#cat<<EOF
eval bcftools isec -C $vartype_arg -p $d $pred $truth 2>>$d/bcftools.log|| exit 1
#EOF
#echo "debug exit" 1>&2; exit 1
fp=$(cat $d/sites.txt | wc -l)
ppv=$(echo "scale=3; $tp/($tp+$fp)" | bc -l)
rm -rf $d
#echo "Keeping $d" 1>&2

#echo "DEBUG tp=$tp p=$p fp=$fp" 1>&2

echo "sens=$sens"
echo "ppv=$ppv"

sens_warn=$(echo "$sens<$sens_thresh" | bc)
if [ $sens_warn == 1 ]; then
    echo "ERROR: SENS<$sens_thresh" 1>&2
    exit 1
fi

ppv_warn=$(echo "$ppv<$ppv_thresh" | bc)
#echo "DEBUG $tp $p $ppv $ppv_warn" 1>&2
if [ $ppv_warn == 1 ]; then
    echo "ERROR: PPV<$ppv_thresh" 1>&2
    exit 1
fi
