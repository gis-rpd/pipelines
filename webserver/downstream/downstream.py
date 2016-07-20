#!/usr/bin/env python3
"""
Retrieves runcomplete records in MongoDB with user-specified parameters for filtering.
Unless specified by -w or --win, only the 7 most recent days of records are retrieved.
"""

#--- standard library imports
#
from argparse import ArgumentParser
from datetime import datetime, timedelta
import os
from pprint import PrettyPrinter
import subprocess
import sys
from time import mktime

#--- third-party imports
#
from flask import Flask, Markup, request, render_template
app = Flask(__name__)

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "../..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from pipelines import generate_window, path_to_url
from mongodb import mongodb_conn
TEST_SERVER = True

__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


def instantiate_args():
    """
    Instantiates argparse object
    """
    instance = ArgumentParser(description=__doc__)
    instance.add_argument("-f", "--flask", nargs="*", help="use web server, specify host & port")
    instance.add_argument("-t", "--testing", action="store_true", help="use MongoDB test-server")
#    instance.add_argument("-s", "--status", \
#        help="filter records by analysis status (STARTED/FAILED/SEQRUNFAILED/SUCCESS)")
#    instance.add_argument("-m", "--mux", help="filter records by mux_id")
#    instance.add_argument("-r", "--run", help="filter records by run")
#    instance.add_argument("-w", "--win", type=int, help="filter records up to specified day(s) ago")
#    instance.add_argument("-a", "--arrange", nargs="*", \
#        help="arrange records by key and order (e.g. --arrange ctime dsc site asc ...)")
    return instance.parse_args()


def instantiate_query(args):
    """
    Instantiates MongoDB query dictionary object
    """
    instance = {}
    if args.status:
        instance["analysis.Status"] = args.status
    if args.mux:
        instance["analysis.per_mux_status.mux_id"] = args.mux
    if args.run:
        instance["run_id"] = {"$regex": "^" + args.run}
    if args.win:
        epoch_present, epoch_initial = generate_window(args.win)
    else:
        epoch_present, epoch_initial = generate_window(7)
    instance["ctime"] = {"$gt": epoch_initial, "$lt": epoch_present}
    return instance


def merge_cells(child_key, key):
    """
    Table cell rendering handler
    """
    result = ""
    if child_key in key:
        if str(key[child_key]) == "STARTED":
            result += ("<span class='label label-pill label-warning'>" \
                + str(key[child_key]) + "</span>")
        elif str(key[child_key]).find("FAILED") != -1 or str(key[child_key]).upper() == "FALSE":
            result += ("<span class='label label-pill label-danger'>" \
                + str(key[child_key]).upper() + "</span>")
        elif str(key[child_key]) == "SUCCESS" or str(key[child_key]).upper() == "TRUE":
            result += ("<span class='label label-pill label-success'>" \
                + str(key[child_key]).upper() + "</span>")
        elif str(key[child_key]) == "TODO":
            result += ("<span class='label label-pill label-default'>" \
                + str(key[child_key]) + "</span>")
        elif str(key[child_key]) == "NOARCHIVE":
            result += ("<span class='label label-pill label-primary'>" \
                + "NO ARCHIVE" + "</span>")
        else:
            result += str(key[child_key])
    return result


@app.route('/', methods=['POST'])
def form_post():
    """
    Flask callback function for POST requests from FORMS
    """
    result = ""
    return form_none(mongodb_conn(TEST_SERVER).gisds.pipeline_runs_copy.find())


@app.route('/')
#def form_none(mongo_results=mongodb_conn(TEST_SERVER).gisds.pipeline_runs_copy.find({"": ""}), nav_caption=""):
def form_none(mongo_results=mongodb_conn(TEST_SERVER).gisds.pipeline_runs_copy.find(), nav_caption=""):
    """
    Flask callback function for all requests
    """
    result = ""
    result += ("<script>$(function(){$('.nav_caption').replaceWith('" \
        + '<span class="nav_caption">' + nav_caption + "</span>" + "');});</script>")
    for record in mongo_results:
        result += "<tr class='run_row'>"
        result += ("<td>" + str(record["lib_id"]) + "</td>")
        result += ("<td>" + str(record["mux_id"]) + "</td>")
        result += ("<td>" + str(record["run_id"]) + "</td>")

        if len(str(record["ctime"])) == 13:
            result += ("<td>" + str(datetime.fromtimestamp(
                record["ctime"] / 1000).isoformat()).replace(":", "-") + "</td>")
        else:
            result += ("<td>" + str(record["ctime"]) + "</td>")
        
        for runcomplete in mongodb_conn(False).gisds.runcomplete.find({"analysis.per_mux_status.mux_id": str(record["mux_id"])}):
            result += "<td>"
            for analysis in runcomplete["analysis"]:
                result += (str(analysis["analysis_id"]) + "<br/>")
            result += "</td>"

        result += "<td>"
        for fastq in record["fastqs"]:
            result += ("<a href='" + path_to_url(fastq) + "'>" + fastq + "</a><br/>")
        result += "</td>"

        result += ("<td>" + str(record["pipeline_name"]) + "</td>")
        result += ("<td>" + str(record["pipeline_version"]) + "</td>")
        result += "<td>"
        result += """
        <table class='table table-bordered table-hover table-fixed table-compact'>
            <thead>
                <tr>
                    <th>GENOME</th>
                    <th>LIBTECH</th>
                </tr>
            </thead>
            <tbody>
                <tr>
        """
        result += ("<td>" + str(record["pipeline_params"]["genome"]) + "</td>")
        result += ("<td>" + str(record["pipeline_params"]["libtech"]) + "</td>")
        result += "</tr></tbody></table>"
        result += "</td>"

        result += ("<td>" + str(record["site"]) + "</td>")
        result += ("<td><a href='" + path_to_url(record["out_dir"]) + "'>" + str(record["out_dir"]) + "</a></td>")
        result += "</tr>"
    return render_template("downstream.html", result=Markup(result))


def main():
    """
    Main function
    """
    args = instantiate_args()

    if args.flask:
        if len(args.flask) == 2:
            app.run(host=args.flask[0], port=args.flask[1])
    else:
        for result in mongodb_conn(args.testing).gisds.pipeline_runs_copy.find():
            PrettyPrinter(indent=2).pprint(result)


if __name__ == "__main__":
    main()
