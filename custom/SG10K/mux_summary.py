#!/usr/bin/env python3
# FIXME hardcoded python because we need for xlsxwriter
"""Creating summary table for SG10K batch
"""

import glob
import os
import csv
import sys

import yaml
import xlsxwriter

WRITE_CSV = False
WRITE_XLS = True
WRITE_CONSOLE = False
SUMMARY_KEYS = ["raw total sequences:",
                #"reads properly paired:",
                'reads properly paired [%]',# ours
                #"reads duplicated:",
                'reads duplicated [%]', # ours
                #"bases mapped (cigar):",
                #'% bases mapped',
                #'base coverage',
                "error rate:",
                'insert size average:',
                'insert size standard deviation:']
ETHNICITIES = ['CHS', 'INS', 'MAS']
MAX_CONT = 0.01999999
MIN_DEPTH = 7
MIN_QC20 = 45*10**9


def parse_summary_from_stats(statsfile):#, genome_size=GENOME_SIZE['hs37d5']):
    """FIXME:add-doc"""

    sn = dict()
    with open(statsfile) as fh:
        for line in fh:
            if not line.startswith("SN"):
                continue
            ls = line.strip().split("\t")[1:]
            sn[ls[0]] = float(ls[1])
        sn['bases mapped [%]'] = 100 * sn["bases mapped (cigar):"]/float(sn["raw total sequences:"] * sn["average length:"])
        sn['reads properly paired [%]'] = 100 * sn["reads properly paired:"]/float(sn["raw total sequences:"])
        sn['reads duplicated [%]'] = 100 * sn["reads duplicated:"]/float(sn["raw total sequences:"])
        #sn['base coverage'] = sn["bases mapped (cigar):"]/float(genome_size)
        return sn



def parse_selfsm(selfsm_file):
    """FIXME:add-doc"""

    with open(selfsm_file) as fh:
        header = fh.readline()[1:].split()
        #print(headers)
        values = fh.readline().split()
        #print(values)
    d = dict(zip(header, values))
    for k in ['AVG_DP', 'FREELK1', 'FREELK0', 'FREEMIX']:
        try:
            d[k] = float(d[k])
        except ValueError:
            pass
    for k in ['#SNPS', '#READS']:
        try:
            d[k] = int(d[k])
        except ValueError:
            pass
    return d



# print(parse_selfsm("WHH1253/out/WHH1253/WHH1253.bwamem.fixmate.mdups.srt.recal.CHS.selfSM"))

def check_completion(conf_yamls, num_expected=96):
    """FIXME:add-doc"""

    print("Verifying completeness based on {} config yaml files...".format(len(conf_yamls)))
    # check completion
    #
    num_complete = 0
    num_incomplete = 0
    # assuming conf.yaml is in run folder
    for f in conf_yamls:
        with open(f) as fh:
            cfg = dict(yaml.safe_load(fh))
        num_samples = len(cfg['samples'])
        snake_log = os.path.join(os.path.dirname(f), "logs/snakemake.log")
        with open(snake_log) as fh:
            loglines = fh.readlines()
            if 'Pipeline run successfully completed' in ''.join(loglines[-10:]):
                num_complete += num_samples
            else:
                num_incomplete += num_samples
    print("{} completed".format(num_complete))
    print("{} incomplete".format(num_incomplete))
    print("(Note, numbers can be misleading for multisample runs (a single failure anywhere fails all samples)")
    assert num_complete == num_expected
    print("Okay. Proceeding...")


def main(conf_yamls):
    """main
    """

    num_expected = 10
    check_completion(conf_yamls, num_expected)

    if WRITE_CSV:
        assert not os.path.exists('summary.csv')
        csvfile = open('summary.csv', 'w')
        print("Writing to summary.csv")
        csvwriter = csv.writer(csvfile, delimiter='\t')
    else:
        print("Not writing cvs-file")

    if WRITE_XLS:
        assert not os.path.exists('summary.xls')
        xls = "summary.xls"
        print("Writing to summary.xls")
        workbook = xlsxwriter.Workbook(xls)
        worksheet = workbook.add_worksheet()

        fmtheader = workbook.add_format({'bold': True, 'align': 'center'})
        fmtintcomma = workbook.add_format({'num_format': '###,###,###,###0'})
        fmt01 = workbook.add_format({'num_format': '0.1'})
        fmt00001 = workbook.add_format({'num_format': '0.0001'})

        worksheet.set_row(0, None, fmtheader)
        worksheet.set_column('B:B', 20, fmtintcomma)
        worksheet.set_column('C:D', None, fmt01)
        worksheet.set_column('F:H', None, fmt01)
        worksheet.set_column('E:E', None, fmt00001)
        worksheet.set_column('I:K', None, fmt00001)
        worksheet.set_column('L:L', 20, fmtintcomma)# qc20

        xls_row_no = 0
    else:
        print("Not writing to xls-file")

    if WRITE_CONSOLE:
        print("Writing to console")
    else:
        print("Not writing to console")

    header = ["sample"]
    for key in SUMMARY_KEYS:
        key = key.strip(" :")
        header.append(key)
    header.append("Avg. Depth")
    for key in ETHNICITIES:
        header.append("Cont. " + key)
    header.append("QC20")
    
    if WRITE_CONSOLE:
        print("\t".join(header))
    if WRITE_CSV:
        csvwriter.writerow(header)
    if WRITE_XLS:
        for xls_col_no, cell_data in enumerate(header):
            worksheet.write(xls_row_no, xls_col_no, cell_data)
        xls_row_no += 1

    for f in conf_yamls:
        outdir = os.path.join(os.path.dirname(f), "out")
        with open(f) as fh:
            cfg = dict(yaml.safe_load(fh))
        for sample in cfg['samples']:

            statsfile = glob.glob(os.path.join(outdir, sample, "*.bwamem.fixmate.mdups.srt.recal.bamstats/stats.txt"))
            assert len(statsfile) == 1
            statsfile = statsfile[0]
            summary = parse_summary_from_stats(statsfile)
            row = [sample]
            row.extend([summary[k] for k in SUMMARY_KEYS])

            selfsm_files = glob.glob(os.path.join(outdir, sample, "*.bwamem.fixmate.mdups.srt.recal.*selfSM"))
            selfsm = dict()
            for f in selfsm_files:
                ethnicity = f.split(".")[-2]
                selfsm[ethnicity] = parse_selfsm(f)
            assert sorted(list(selfsm.keys())) == sorted(ETHNICITIES)

            #avg_dp = set([v['AVG_DP'] for v in selfsm.values()])
            #assert len(avg_dp) == 1, avg_dp
            # rounding errors
            avg_dp = set([v['AVG_DP'] for v in selfsm.values()])
            avg_dp = list(avg_dp)[0]
            if avg_dp < MIN_DEPTH:
                sys.stderr.write("DP threshold reached for {}: {} < {}\n".format(sample, avg_dp, MIN_DEPTH))
            row.append(avg_dp)

            for e in ETHNICITIES:
                cont = selfsm[e]['FREEMIX']
                if cont > MAX_CONT:
                    sys.stderr.write("CONT threshold reached for {}: {} > {}\n".format(sample, cont, MAX_CONT))
                row.append(cont)

            qc20_file = glob.glob(os.path.join(outdir, sample, "*.bwamem.fixmate.mdups.srt.recal.qc.txt"))
            if qc20_file:
                qc20_file = qc20_file[0]
                with open(qc20_file) as fh:
                    l = fh.readline()
                qc20 = int(l.split()[-1])
                if qc20 < MIN_QC20:
                    sys.stderr.write("qc20 smaller threshold for {}: {} < {}\n".format(sample, qc20, MIN_QC20))
            else:
                sys.stderr.write("qc20 missing for {}\n".format(sample))
                qc20 = ""
            row.append(qc20)
                    
            if WRITE_CONSOLE:
                print("\t".join(["{}".format(v) for v in row]))
            if WRITE_CSV:
                csvwriter.writerow(row)
            if WRITE_XLS:
                for xls_col_no, cell_data in enumerate(row):
                    worksheet.write(xls_row_no, xls_col_no, cell_data)
                xls_row_no += 1

    if WRITE_CSV:
        csvfile.close()
    if WRITE_XLS:
        workbook.close()
        print("Please format xls file now and mark any outliers report above")

    print("Successful completion")


if __name__ == "__main__":
    conf_yamls = sys.argv[1:]
    assert conf_yamls, ("No conf.yaml file/s given as argument")
    assert all([os.path.exists(f) for f in conf_yamls])
    main(conf_yamls)
