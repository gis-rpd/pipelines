#!/usr/bin/env python3
"""Bcl2fastq QC checks

We are running bcl2fastq per MUX, hence one demux html input
corresponds to one MUX. Since a single lane cannot hold more than one
MUX, the lane info contained in one html is complete. In other words,
all/all/all/lane.html contains info for all lanes in which
this mux was (and includes samples in this MUX plus
'undetermined'). Since MUXs cannot be shared in a lane it follows this
file contains all info for the resp. lanes.

However the flowcell info is incomplete and only reflects data in the
listed lanes. To get the full flowcell info demux htmls from all MUXes
have to be summed up.

'Undetermined' specific info is separately listed in
default/Undetermined/unknown/lane.html

"""

#--- standard library imports
#
import sys
import os
import glob
import re
import pprint
from collections import OrderedDict
import argparse
import logging

#--- third-party imports
#
import yaml

#--- project specific imports
#
from html_table_parser import HTMLTableParser
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from config import bcl2fastq_qc_conf as config
from pipelines import is_devel_version
from pipelines import email_for_user
from pipelines import send_mail
from pipelines import path_to_url

__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2017 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


# global logger
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '[{asctime}] {levelname:8s} {filename} {message}', style='{'))
logger.addHandler(handler)


DEMUX_HTML_FILE_PATTERN = r'.*Project_(\w+)/html/([\w-]+)/\w+/\w+/\w+/lane.html'


def get_machine_type_from_run_num(run_num):
    """these are the values to be used in config for machine dependent settings"""
    id_to_machine = {
        'MS001': 'miseq',
        'NS001': 'nextseq',
        'HS001': 'hiseq 2500 rapid',
        'HS002': 'hiseq 2500',
        'HS003': 'hiseq 2500',
        'HS004': 'hiseq 2500',
        'HS005': 'macrogen',
        'HS006': 'hiseq 4000',
        'HS007': 'hiseq 4000',
    }
    machine_id = run_num.split('-')[0]
    machine_type = id_to_machine[machine_id]
    return machine_type


def email_qcfails(subject, body):
    """email qc failures
    """
    if is_devel_version():
        toaddr = email_for_user()
        ccaddr = None
    else:
        toaddr = config['email']
        ccaddr = "rpd@gis.a-star.edu.sg"

    send_mail(subject, body, toaddr=toaddr, ccaddr=ccaddr,
              pass_exception=False)

def htmlparser_demux_table_to_dict(table_in, decimal_mark=".", thousands_sep=","):
    """cleans raw bcl2fastq html table formatting as created by htmlparser
    and converts to OrderedDict using sequential row numbers as first
    key (i.e. row[0][key] = value)
    """

    assert decimal_mark != thousands_sep
    table_out = OrderedDict()
    header = table_in[0]
    for row_no, row in enumerate(table_in[1:]):
        table_out[row_no] = OrderedDict()
        for k, v in OrderedDict(zip(header, row)).items():
            #print("RAW", k, v)
            if thousands_sep:
                v = v.replace(thousands_sep, "")
            if v == "NaN":
                v = None
            elif decimal_mark in v:
                v = float(v)
            elif len(v):
                v = int(v)
            else:
                v = None
            table_out[row_no][k] = v
            #print(k, ":", v)
        #print()
    return table_out


def process_demux_html(html_file):
    """returns flowcell summary and lane summary as dicts"""

    with open(html_file, encoding='utf-8') as fh:
        html_data = fh.read()
    p = HTMLTableParser()
    p.feed(html_data)

    assert len(p.tables) == 3, (
        "Parsing tables from {} failed".format(html_file))
    flowcell_id = p.tables[0][0][0].split()[0]# html parsing sucks
    flowcell_htmlparser_table = p.tables[1]
    lane_htmlparser_table = p.tables[2]

    # clean up flowcell table
    #
    flowcell_table = htmlparser_demux_table_to_dict(flowcell_htmlparser_table)
    # htmlparser_demux_table_to_dict() creates rows which don't make
    # sense for flowcell, so we rename the sole row 0 to flowcell_id
    assert len(flowcell_table) == 1
    flowcell_table[flowcell_id] = flowcell_table.pop(0)

    # clean up lane table
    #
    lane_table = htmlparser_demux_table_to_dict(lane_htmlparser_table)
    # htmlparser_demux_table_to_dict() creates sequentially numbered
    # rows but we want to use the lane numbers as keys. has to happen
    # in two iterations, to avoid overwriting existing keys
    row_idxs = list(lane_table.keys())
    for row_idx in row_idxs:# can't mutate during key iteration
        d = lane_table.pop(row_idx)
        k = "Lane " + str(d['Lane'])
        del d['Lane']
        lane_table[k] = d
    # now convert back to int/lane
    row_idxs = list(lane_table.keys())
    for row_idx in row_idxs:# can't mutate during key iteration
        d = lane_table.pop(row_idx)
        assert row_idx.startswith("Lane ")
        k = int(row_idx.split()[1])
        lane_table[k] = d

    return flowcell_table, lane_table


def gather_demux_stats(demux_html_files):
    """Parse all demux html stats, parse and combine (logically
    representing one run). Teturn flowcell summary table and lane
    summary table as two dicts()
    """

    flowcell_table = OrderedDict()
    lane_table = OrderedDict()

    # extract tables from all demux_html_files
    #
    for html_file in demux_html_files:
        m = re.search(DEMUX_HTML_FILE_PATTERN, html_file)
        if not m or not len(m.groups()) == 2:
            logger.fatal("html file name (%s) doesn't match"
                         " expected pattern (%s)\n",
                         html_file, DEMUX_HTML_FILE_PATTERN)
            sys.exit(1)

        #mux_id = m.groups()[0]
        flowcell_id = m.groups()[1]
        logger.info("Reading %s", html_file)
        this_flowcell_table, this_lane_table = process_demux_html(html_file)
        # pure paranoia test
        assert [flowcell_id] == list(this_flowcell_table.keys())

        for lane in this_lane_table.keys():
            assert lane not in lane_table.keys(), (
                "Seen lane {} before, i.e. html files are not from same run".format(lane))
        lane_table.update(this_lane_table)

        if not flowcell_id in flowcell_table:
            flowcell_table = this_flowcell_table
        else:
            for k, v in this_flowcell_table[flowcell_id].items():
                flowcell_table[flowcell_id][k] += v

    return flowcell_table, lane_table



def run_qc_checks(project_dirs, machine_type):
    """main function"""
    qcfails = []
    assert len(project_dirs) >= 1

    # determine all all/all/all/lane.html in project subdirs of given demux_dir
    #
    demux_html_files = []
    for d in project_dirs:
        g = os.path.join(d, 'html/*/all/all/all/lane.html')
        f = glob.glob(g)
        assert len(f) == 1, (
            "Was expecting exactly one matching demux html"
            " but found {} for glob {}".format(f, g))
        demux_html_files.extend(f)
    flowcell_table, lane_table = gather_demux_stats(demux_html_files)
    logger.debug("# Combined Flowcell Summary")
    logger.debug(pprint.pformat(flowcell_table))
    logger.debug("# Combined per Lane")
    logger.debug(pprint.pformat(lane_table))

    for lane, values in lane_table.items():
        # test: pf
        v = int(values['PF Clusters'] / 1000000.0)
        l = config['min-pf-cluster-in-mil'][machine_type]
        if v < float(l):
            qcfails.append(
                "PF clusters under limit"
                " ({} < {}) for lane {}".format(v, l, lane))
        logger.fatal("v=%s l=%s machine_type=%s", v, l, machine_type)
        if v == 0:
            # no passed reads? no point in continuing checks
            continue
        
        # test: perfect barcode
        v = values['% Perfect barcode']
        l = config['min-percent-perfect-barcode']
        if v is not None:# muxed input
            if v < float(l):
                qcfails.append(
                    "Percent perfect barcode under limit"
                    " ({} < {}) for lane {}".format(v, l, lane))

        # test: Q30 bases
        v = values['% >= Q30 bases']
        l = config['min-percent-q30-bases'][machine_type]
        if v < float(l):
            qcfails.append(
                "Percent Q30 bases under limit"
                " ({} < {}) for lane {}".format(v, l, lane))

        # test: yield
        v = values['Yield (Mbases)'] / 1000.0
        l = config['min-lane-yield-gb'][machine_type]
        if v < float(l):
            qcfails.append(
                "Yield under limit"
                " ({} < {}) for lane {}".format(v, l, lane))

        

    # info about 'undetermined' sits elsewhere (only makes sense if demuxed)
    #
    undet_demux_html_files = []
    for d in project_dirs:
        g = os.path.join(d, 'html/*/default/Undetermined/all/lane.html')
        f = glob.glob(g)
        if f:
            # otherwise probably non-muxed
            undet_demux_html_files.extend(f)
    # for non-demuxed input (empty input files) everything below still works as expected
    _, undet_lane_table = gather_demux_stats(undet_demux_html_files)
    logger.debug("# Undetermined combined per Lane")
    logger.debug(pprint.pformat(undet_lane_table))

    # test: undetermined reads
    #
    for lane, values in undet_lane_table.items():
        v = values['% of the lane']
        l = config['max-percent-undetermined']
        if v is not None:# muxed input
            if v > float(l):
                qcfails.append(
                    "Percent undetermined reads exceeding limits"
                    " ({} > {}) for lane {}".format(v, l, lane))
    return qcfails


def main():
    """main function
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-d', "--bcl2fastq-dir", required=True,
                        help="bcl2fastq directory (containing a conf.yaml)")
    parser.add_argument('--no-mail', action='store_true',
                        help="Don't send email on detected failures")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Increase verbosity")
    parser.add_argument('-q', '--quiet', action='count', default=0,
                        help="Decrease verbosity")
    args = parser.parse_args()

    # Repeateable -v and -q for setting logging level.
    # See https://www.reddit.com/r/Python/comments/3nctlm/what_python_tools_should_i_be_using_on_every/
    # and https://gist.github.com/andreas-wilm/b6031a84a33e652680d4
    # script -vv -> DEBUG
    # script -v -> INFO
    # script -> WARNING
    # script -q -> ERROR
    # script -qq -> CRITICAL
    # script -qqq -> no logging at all
    logger.setLevel(logging.WARN + 10*args.quiet - 10*args.verbose)

    assert os.path.isdir(args.bcl2fastq_dir)
    conf_file = os.path.join(args.bcl2fastq_dir, 'conf.yaml')
    if not os.path.exists(conf_file):
        logger.fatal("Expected config file missing: %s", conf_file)
        sys.exit(1)
    with open(conf_file) as fh:
        bcl2fastq_cfg = yaml.safe_load(fh)

    run_num = bcl2fastq_cfg["run_num"]
    machine_type = get_machine_type_from_run_num(run_num)

    project_dirs = []
    for _, mux_info in bcl2fastq_cfg["units"].items():
        d = os.path.join(args.bcl2fastq_dir, "out", mux_info['mux_dir'])
        if not os.path.exists(d):
            logger.warning("Ignoring missing directory %s", d)
        else:
            project_dirs.append(d)

    if len(project_dirs) == 0:
        logger.error("Exiting because no project directories where found in %s", args.bcl2fastq_dir)
        sys.exit(1)
        
    qcfails = run_qc_checks(project_dirs, machine_type)

    if qcfails:
        subject = "bcl2fastq QC checks failed for {} ({}):".format(
            run_num, args.bcl2fastq_dir)
        body = "The following " + subject
        for f in qcfails:
            body += "\n- {}".format(f)
        body += "\nPlease double-check here: {}\n".format(
            path_to_url(args.bcl2fastq_dir))
        body += "QC_FAILED"# signal for callers
        print(subject + "\n" + body)

        if not args.no_mail:
            email_qcfails(subject, body)
    else:
        print("QC checks completed. No tests failed")
        print("QC SUCCESS")# signal for callers


if __name__ == '__main__':
    main()
