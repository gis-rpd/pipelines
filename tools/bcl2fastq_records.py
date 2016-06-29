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
    return instance.parse_args()


def instantiate_mongo(testing):
    """
    Instantiates MongoDB database object
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


@app.route('/')
@app.route('/', methods=['POST'])
def form_post():
    mongo = instantiate_mongo(True)
    instance = {}
#    instance[request.form['text'].split(" ")[0]] = request.form['text'].split(" ")[1]
    epoch_present, epoch_initial = generate_window(365)
    instance["timestamp"] = {"$gt": epoch_initial, "$lt": epoch_present}

    result = ""
    for record in mongo.find(instance):
        result += "<tr>"
#        result += ("<td>" + str(record["analysis.Status"]) + "</td>")
#        result += ("<td>" + str(record["analysis.per_mux_status.mux_id"]) + "</td>")
        result += ("<td>" + str(record["run"]) + "</td>")
        result += ("<td>" + str(record["timestamp"]) + "</td>")
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
        for record in mongo.find(query):
            PrettyPrinter(indent=2).pprint(record)

if __name__ == "__main__":
#    app.run(debug=True)
    main()
