#!/usr/bin/env python3
"""
Retrieves runcomplete records in MongoDB with user-specified parameters for filtering.
Unless specified by -w or --win, only the 7 most recent days of records are retrieved.
"""

#--- standard library imports
#
from argparse import ArgumentParser
import os
from pprint import PrettyPrinter
import subprocess
import sys

#--- third-party imports
#/
from flask import Flask, Markup, request, render_template
app = Flask(__name__)

#--- project specific imports
#
# add lib dir for this pipeline installation to PYTHONPATH
LIB_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "lib"))
if LIB_PATH not in sys.path:
    sys.path.insert(0, LIB_PATH)
from pipelines import generate_window
# FIXME: that function should go into lib
sys.path.insert(0, os.path.join(LIB_PATH, "..", "bcl2fastq"))
from mongo_status import mongodb_conn


__author__ = "Andreas Wilm"
__email__ = "wilma@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


def send_email(email, subject, message):
    """
    send_email("rpd@mailman.gis.a-star.edu.sg", "[RPD] " + os.path.basename(__file__), dictionary_checker())
    """
    subprocess.getoutput("echo '" + message + "' | mail -s '" + subject + "' " + email)


def dictionary_checker():
    send_email("rpd@mailman.gis.a-star.edu.sg", "[RPD] " + os.path.basename(__file__), "")


def instantiate_args():
    """
    Instantiates argparse object
    """
    instance = ArgumentParser(description=__doc__)
    instance.add_argument("-f", "--flask", action="store_true", help="use web server")
    instance.add_argument("-t", "--testing", action="store_true", help="use MongoDB test-server")
    instance.add_argument(
        "-s", "--status", help="filter records by analysis status (STARTED/FAILED/SUCCESS)")
    instance.add_argument("-m", "--mux", help="filter records by mux_id")
    instance.add_argument("-r", "--run", help="filter records by run")
    instance.add_argument("-w", "--win", type=int, help="filter records up to specified day(s) ago")

#    instance.add_argument("-a", "--arrange", help="arrange records by key and order")
    return instance.parse_args()


def instantiate_mongo(testing):
    """
    Instantiates MongoDB database object
    For Test Server, testing == true
    For Production Server, testing == false
    """
    return mongodb_conn(testing).gisds.runcomplete


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
        instance["run"] = args.run
    if args.win:
        epoch_present, epoch_initial = generate_window(args.win)
    else:
        epoch_present, epoch_initial = generate_window(7)
    instance["timestamp"] = {"$gt": epoch_initial, "$lt": epoch_present}
    return instance


def merge_cells(parent_key, child_key, record):
    result = "<td>"
    if parent_key in record:
        for key in record[parent_key]:
            if child_key in key:
                result += str(key[child_key])
            result += "<p/>"
    result += "</td>"
    return result


@app.route('/')
@app.route('/', methods=['POST'])
def form_post():
    """
    Flask Callback Function
    """
    mongo = instantiate_mongo(False)
#    instance = {}
#    instance[request.form['text'].split(" ")[0]] = request.form['text'].split(" ")[1]
#    epoch_present, epoch_initial = generate_window(365)
#    instance["timestamp"] = {"$gt": epoch_initial, "$lt": epoch_present}

    result = ""
    for record in mongo.find():
        result += "<tr>"

        result += ("<td>" + str(record["run"]) + "</td>")
        result += ("<td>" + str(record["timestamp"]) + "</td>")

        result += "<td>"

        result += """
        <table class='table table-bordered table-hover table-fixed'>
            <thead>
                <tr>
                    <th>STATUS</th>
                    <th>ANALYSIS_ID</th>
                    <th>END_TIME</th>
                    <th>OUT_DIR</th>
                    <th>USER_NAME</th>
                    <th>MUX</th>
                </tr>
            </thead>
            <tbody>
        """

        if "analysis" in record:
            for key in record["analysis"]:
                result += "<tr><td>"
                if "Status" in key:
                    if(type(key) == dict):
                        if (str(key["Status"]) == "STARTED"):
                            result += ("<span class='label label-pill label-warning'>" + str(key["Status"]) + "</span>")
                        elif (str(key["Status"]) == "FAILED"):
                            result += ("<span class='label label-pill label-danger'>&nbsp&nbsp" + str(key["Status"]) + "!&nbsp&nbsp</span>")
                        elif (str(key["Status"]) == "SUCCESS"):
                            result += ("<span class='label label-pill label-success'>" + str(key["Status"]) + "</span>")
                        else:
                            result += str(key["Status"])
#                    if(type(key) == str):
#                        result += key
                result += merge_cells("analysis", "analysis_id", record)
                result += merge_cells("analysis", "end_time", record)
                result += merge_cells("analysis", "out_dir", record)
                result += merge_cells("analysis", "user_name", record)
#                result += "</td></tr>"
                
                result += "<td>"
                result += """
                <table class='table table-bordered table-hover table-fixed'>
                    <thead>
                        <tr>
                            <th>MUX_ID</th>
                        </tr>
                    </thead>
                    <tbody>
                """

                if "analysis" in record:
                    for analysis_set in record["analysis"]:
                        result += "<tr><td>"
#                        result += merge_cells("per_mux_status", "mux_id", analysis_set)
                        
                        if "per_mux_status" in analysis_set:
                            for mux_set in analysis_set["per_mux_status"]:
#                                if mux_set is not None:
                                if "mux_id" in mux_set:
                                    result += str(mux_set["mux_id"])
                                result += "<p/>"

                        result += "</td></tr>"
                result += "</tbody></table>"
                result += "</td>"

        result += "</tbody></table>"

        result += "</td>"

        result += "</td></tr>"

        result += "</tr>"
    return render_template("index.html", result=Markup(result))


def main():
    """
    Main function
    export FLASK_APP=bcl2fastq_records.py
    flask run --host=0.0.0.0
    """
    args = instantiate_args()
    mongo = instantiate_mongo(args.testing)
    query = instantiate_query(args)

    if args.flask:
        os.environ["FLASK_APP"] = os.path.basename(__file__)
        os.system("flask run --host=0.0.0.0")
        app.run()
    else:
        for record in mongo.find(query).sort([("run", -1), ("timestamp", -1)]):
            PrettyPrinter(indent=2).pprint(record)

if __name__ == "__main__":
#    app.run(debug=True)
    main()
