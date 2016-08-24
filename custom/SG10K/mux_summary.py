#!/mnt/projects/rpd/apps.testing/miniconda3/envs/jupyter/bin/python

import glob
import os
import csv
import sys
import xlsxwriter

WRITE_CSV = False
WRITE_XLS = True
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



def parse_summary_from_stats(statsfile):#, genome_size=GENOME_SIZE['hs37d5']):
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


def main():
    """main
    """

    print("Verifying completeness...")
    complete = []
    incomplete = []
    for yaml in glob.glob("W*yaml"):
        sampledir = yaml.replace(".yaml", "/")
        with open(os.path.join(sampledir, "logs/snakemake.log")) as fh:
            loglines = fh.readlines()
            if 'Pipeline run successfully completed' in ''.join(loglines[-10:]):
                complete.append(sampledir)
            else:
                incomplete.append(sampledir)
    print("{} completed".format(len(complete)))
    print("{} incomplete".format(len(incomplete)))
    assert len(complete) == 96
    print("Okay. Proceeding...")

    if WRITE_CSV:
        assert not os.path.exists('summary.csv')
        csvfile = open('summary.csv', 'w')
        print("Writing to summary.csv")
        csvwriter = csv.writer(csvfile, delimiter='\t')
    if WRITE_XLS:
        assert not os.path.exists('summary.xls')
        xls = "summary.xls"
        print("Writing to summary.xls")
        workbook = xlsxwriter.Workbook(xls)
        worksheet = workbook.add_worksheet()
        xls_row_no = 0

    header = ["sample"]
    for key in SUMMARY_KEYS:
        key = key.strip(" :")
        header.append(key)
    header.append("Avg. Depth")
    for key in ETHNICITIES:
        header.append("Cont. " + key)

    print("\t".join(header))
    if WRITE_CSV:
        csvwriter.writerow(header)
    if WRITE_XLS:
        for xls_col_no, cell_data in enumerate(header):
            worksheet.write(xls_row_no, xls_col_no, cell_data)
        xls_row_no += 1

    for yaml in glob.glob("W*yaml"):
        sample = yaml.replace(".yaml", "")
        sampledir = sample
        statsfile = glob.glob(os.path.join(sampledir, "out/*/*.bwamem.fixmate.mdups.srt.recal.bamstats/stats.txt"))
        assert len(statsfile)==1
        statsfile = statsfile[0]
        summary = parse_summary_from_stats(statsfile)
        row = [sample]
        row.extend([summary[k] for k in SUMMARY_KEYS])

        selfsm_files = glob.glob(os.path.join(sampledir, "out/*/*.bwamem.fixmate.mdups.srt.recal.*selfSM"))
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

    print("Successful completion")


if __name__ == "__main__":
    main()

    
