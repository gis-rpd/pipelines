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
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from pipelines import generate_window, path_to_url
from mongodb import mongodb_conn


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


def instantiate_args():
    """
    Instantiates argparse object
    """
    instance = ArgumentParser(description=__doc__)
    instance.add_argument("-f", "--flask", action="store_true", help="use web server")
    instance.add_argument("-j", "--jobNo", help="filter records by jobNo of jobs")
    instance.add_argument("-o", "--owner", help="filter records by owner of jobs")
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
        instance["run"] = {"$regex": "^" + args.run}
    if args.win:
        epoch_present, epoch_initial = generate_window(args.win)
    else:
        epoch_present, epoch_initial = generate_window(7)
    instance["timestamp"] = {"$gt": epoch_initial, "$lt": epoch_present}
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
        else:
            result += str(key[child_key])
    return result


@app.route('/', methods=['POST'])
def form_post():
    """
    Flask callback function for POST requests from FORMS
    """
    list_from = request.form["from"].split("-")
    list_to = request.form["to"].split("-")
    if "-".join(list_from) != "" or "-".join(list_to) != "":
        if len(list_from) == 3 and len(list_to) == 3:
            print("DATE FILTER: FROM " + "-".join(list_from) + " TO " + "-".join(list_to))
            epoch_initial = int(mktime(datetime(int(list_from[0]), int(list_from[1]), \
                int(list_from[2])).timetuple()) * 1000)
            epoch_final = int(mktime((datetime(int(list_to[0]), int(list_to[1]), int(list_to[2])) \
                + timedelta(days=1)).timetuple()) * 1000)
            instance = {}
            instance["timestamp"] = {"$gte": epoch_initial, "$lt": epoch_final}
#            instance["analysis"] = {"$exists": True}
            return form_none(mongodb_conn(False).gisds.accountinglogs.find(instance), \
                "RUNS FROM " + "-".join(list_from) + " TO " + "-".join(list_to))

    return form_none(mongodb_conn(False).gisds.accountinglogs.find({"": ""}))


@app.route('/')
def form_none(mongo_results=mongodb_conn(False).gisds.accountinglogs.find({"": ""}), nav_caption=""):
    """
    Flask callback function for all requests
    """
    result = ""
    result += ("<script>$(function(){$('.nav_caption').replaceWith('" \
        + '<span class="nav_caption">' + nav_caption + "</span>" + "');});</script>")
    analysis_none = 0
    analysis_started = 0
    analysis_failed = 0
    analysis_success = 0
    for record in mongo_results:
        result += "<tr class='run_row'>"
        result += ("<td>" + str(record["run"]) + "</td>")

        if len(str(record["timestamp"])) == 13:
            result += ("<td>" + str(datetime.fromtimestamp(
                record["timestamp"] / 1000).isoformat()).replace(":", "-") + "</td>")
        else:
            result += ("<td>" + str(record["timestamp"]) + "</td>")

        result += "<td>"
        if "analysis" in record:

            if "Status" in record["analysis"][-1]:
                if record["analysis"][-1]["Status"] == "STARTED":
                    analysis_started += 1
                if record["analysis"][-1]["Status"].find("FAILED") != -1:
                    analysis_failed += 1
                if record["analysis"][-1]["Status"] == "SUCCESS":
                    analysis_success += 1

            result += """
            <table class='table table-bordered table-hover table-fixed table-compact'>
                <thead>
                    <tr>
                        <th>ANALYSIS_ID</th>
                        <th>END_TIME</th>
                        <th>OUT_DIR</th>
                        <th>STATUS</th>
                        <th>MUX</th>
                    </tr>
                </thead>
                <tbody>
            """
            for analysis in record["analysis"]:
                result += "<tr>"
                result += ("<td>" + merge_cells("analysis_id", analysis) + "</td>")
                result += ("<td>" + merge_cells("end_time", analysis) + "</td>")
                result += ("<td><a href='" + path_to_url(
                    merge_cells("out_dir", analysis)).replace("//", "/").replace(":/", "://") \
                    + "'>" + merge_cells("out_dir", analysis).replace("//", "/") + "</a></td>")
                result += ("<td>" + merge_cells("Status", analysis) + "</td>")
                result += "<td>"

                if "per_mux_status" in analysis:
                    result += """
                    <table class='table table-bordered table-hover table-fixed table-compact'>
                        <thead>
                            <tr>
                                <th>MUX_ID</th>
                                <th>ARCHIVE</th>
                                <th>DOWNSTREAM</th>
                                <th>STATS</th>
                                <th>STATUS</th>
                                <th>EMAIL</th>                            
                            </tr>
                        </thead>
                        <tbody>
                    """
                    for mux in analysis["per_mux_status"]:
                        result += "<tr>"
                        result += ("<td>" + merge_cells("mux_id", mux) + "</td>")
                        result += ("<td>" + merge_cells("ArchiveSubmission", mux) + "</td>")
                        result += ("<td>" + merge_cells("DownstreamSubmission", mux) + "</td>")
                        result += ("<td>" + merge_cells("StatsSubmission", mux) + "</td>")
                        result += ("<td>" + merge_cells("Status", mux) + "</td>")
                        result += ("<td>" + merge_cells("email_sent", mux) + "</td>")
                        result += "</tr>"
                    result += "</tbody></table>"
                else:
#                    result += "<span class='label label-pill label-default'>NONE</span>"
                    result += """
                    <table class='table table-bordered table-hover table-fixed table-compact invisible'>
                        <thead>
                            <tr>
                                <th>MUX_ID</th>
                                <th>ARCHIVE</th>
                                <th>DOWNSTREAM</th>
                                <th>STATS</th>
                                <th>STATUS</th>
                                <th>EMAIL</th>                            
                            </tr>
                        </thead>
                        <tbody>
                    """
                    result += "</tbody></table>"

                result += "</td>"
            result += "</tbody></table>"
        else:
            analysis_none += 1
            result += "<span class='label label-pill label-default'>NONE</span>"
        result += "</td>"
        result += "</tr>"
        result += "</tr>"

        result += ("<script>$(function(){$('#analysis_none').attr('data-badge', '" \
            + str(analysis_none) + "');});</script>")
        result += ("<script>$(function(){$('#analysis_started').attr('data-badge', '" \
            + str(analysis_started) + "');});</script>")
        result += ("<script>$(function(){$('#analysis_failed').attr('data-badge', '" \
            + str(analysis_failed) + "');});</script>")
        result += ("<script>$(function(){$('#analysis_success').attr('data-badge', '" \
            + str(analysis_success) + "');});</script>")

    return render_template("index.html", result=Markup(result))


def main():
    """
    Main function
    export FLASK_APP=bcl2fastq_records.py
    flask run --host=0.0.0.0
    """
    args = instantiate_args()

    if args.flask:
        if len(args.flask) == 2:
            app.run(host=args.flask[0], port=args.flask[1])
    else:
        selection = {}
        if args.jobNo:
            selection["jobs.jobNo"] = args.jobNo
        if args.owner:
            selection["jobs.owner"] = args.owner
        
        projection = {}
        projection["jobs"] = 1

#        print(str(selection) + ", " + str(projection))
        for result in mongodb_conn(False).gisds.accountinglogs.find(selection, projection):
            for job in result["jobs"]: 
                if job["jobNo"] == args.jobNo:
                    PrettyPrinter(indent=2).pprint(job)

if __name__ == "__main__":
#    app.run(debug=True)
    main()
