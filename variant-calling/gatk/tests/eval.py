#!/usr/bin/env python3
"""Evaluate variant call predictions against GiaB truth
"""

import sys
import tempfile
import os
import shutil
import subprocess
#import gzip
#import glob
#import io

from conf import load_conf


CONF = load_conf()
assert os.path.exists(CONF['highconf_regions'])
for f in CONF['truth_vcf'].values():
    assert os.path.exists(f)
    

def num_vars_from_vcf(f):
    cmd = "zgrep -vc '^#' {}".format(f)
    res = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
    return int(res.decode().strip())


def main(vartype, predvcf, truthvcf):
    """main function"""

    for tool in ['zgrep', 'tabix', 'bcftools']:
        assert shutil.which(tool), "FATAL: {} not in PATH".format(tool)

    outdir = tempfile.mkdtemp()

    outvcf = os.path.join(outdir, os.path.basename(predvcf).replace("vcf.gz", ""))
    outvcf += ".{}-pass-bedovlp.vcf.gz".format(vartype)
    # extract PASSed variants of this type and overlapping with high confidence regions
    cmd = "bcftools view -f .,PASS -v {type} -R {bed} {vcf} -O z -o {outvcf}".format(
        type=vartype, vcf=predvcf, bed=CONF['highconf_regions'], outvcf=outvcf)
    _ = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)

    # index
    cmd = "tabix {outvcf}".format(outvcf=outvcf)
    _ = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)

    # intersect with truth
    isec_outdir = os.path.join(outdir, "isec")
    cmd = "bcftools isec {truth} {outvcf} -p {outdir}".format(
        truth=truthvcf, outvcf=outvcf, outdir=isec_outdir)
    _ = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)


    # bgzip and index intersection vcfs
    #for v in glob.glob(os.path.join(isec_outdir, "*[012].vcf")):# don't bgzip massive unused 0003
    #    cmd = "bgzip {v} && tabix {v}.gz".format(v=v)
    #    _ = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)

    cls = dict()
    for vcffile, cat in [(os.path.join(isec_outdir, "0000.vcf"), "FN"),
                         (os.path.join(isec_outdir, "0001.vcf"), "FP"),
                         (os.path.join(isec_outdir, "0002.vcf"), "TP")]:
        numvars = num_vars_from_vcf(vcffile)
        #print("{}\t{}".format(cat, numvars))
        cls[cat] = numvars
    tpr = cls['TP']/float(cls['TP'] + cls['FN'])
    ppv = cls['TP']/float(cls['TP'] + cls['FP'])

    failed_exp = False
    if tpr < CONF['min_expect'][vartype]['TPR']:
        sys.stderr.write("ERROR: TPR of {:4f} below minimum of {:4f}\n".format(
            tpr, CONF['min_expect'][vartype]['TPR']))
        failed_exp = True
    else:
        print("OK: TPR={:4f}".format(tpr))

    if ppv < CONF['min_expect'][vartype]['PPV']:
        sys.stderr.write("ERROR: PPV of {:4f} below minimum of {:4f}\n".format(
            ppv, CONF['min_expect'][vartype]['PPV']))
        failed_exp = True
    else:
        print("OK: PPV={:4f}".format(ppv))

    shutil.rmtree(outdir)

    if failed_exp:
        sys.exit(1)


if __name__ == "__main__":
    assert len(sys.argv) == 3
    vartype = sys.argv[1]
    predvcf = sys.argv[2]
    try:
        truthvcf = CONF['truth_vcf'][vartype]
    except KeyError:
        sys.stderr.write("FATAL: available variant types: {}\n".format(
            ", ".join(CONF['truth_vcf'].keys())))
        raise
    assert os.path.exists(predvcf)
    main(vartype, predvcf, truthvcf)
