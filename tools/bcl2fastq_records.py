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


__author__ = "LIEW Jun Xian"
__email__ = "liewjx@gis.a-star.edu.sg"
__copyright__ = "2016 Genome Institute of Singapore"
__license__ = "The MIT License (MIT)"


def send_email(email, subject, message):
	"""
	Send alert email for inconsistent MongoDB records
	"""
	subprocess.getoutput("echo '" + message + "' | mail -s '" + subject + "' " + email)


def instantiate_args():
	"""
	Instantiates argparse object
	"""
	instance = ArgumentParser(description=__doc__)
	instance.add_argument("-f", "--flask", action="store_true", help="use web server")
	instance.add_argument("-t", "--testing", action="store_true", help="use MongoDB test-server")
	instance.add_argument("-s", "--status", \
		help="filter records by analysis status (STARTED/FAILED/SEQRUNFAILED/SUCCESS)")
	instance.add_argument("-m", "--mux", help="filter records by mux_id")
	instance.add_argument("-r", "--run", help="filter records by run")
	instance.add_argument("-w", "--win", type=int, help="filter records up to specified day(s) ago")
	instance.add_argument("-a", "--arrange", nargs="*", \
		help="arrange records by key and order (e.g. --arrange timestamp dsc end_time asc ...)")
	return instance.parse_args()


def instantiate_mongo(testing):
	"""
	Instantiates MongoDB database object
	For Test Server, testing == True
	For Production Server, testing == False
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
			return form_none(instantiate_mongo(False).find(instance), \
				"RUNS FROM " + "-".join(list_from) + " TO " + "-".join(list_to))

	return form_none(instantiate_mongo(False).find({"": ""}))


@app.route('/')
def form_none(mongo_results=instantiate_mongo(False).find({"": ""}), nav_caption=""):
	"""
	Flask callback function for all requests
	path_to_url: /mnt/projects/userrig/solexa/.. -> rpd/userrig/runs/solexaProjects/..
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
					result += "<div class='hidden'>FINAL_STARTED</div>" 
#                		elif record["analysis"][-1]["Status"].find("FAILED") != -1:
				elif record["analysis"][-1]["Status"] == "FAILED":
					analysis_failed += 1
					result += "<div class='hidden'>FINAL_FAILED</div>" 
				elif record["analysis"][-1]["Status"] == "SUCCESS":
					analysis_success += 1
					result += "<div class='hidden'>FINAL_SUCCESS</div>" 
				else:
					result += "<div class='hidden'>FINAL_SEQRUNFAILED</div>"
#			else:
#				result += "<div class='hidden'>FINAL_NONE</div>"

			result += """
			<table class='table table-bordered table-hover table-fixed table-compact analysis_table'>
				<thead>
					<tr>
						<th>ANALYSIS_ID</th>
						<th>END_TIME</th>
						<th>OUT_DIR</th>
						<th>STATUS</th>
						<th>MUX</th>
					</tr>
				</thead>
				<tbody class='analysis_tbody'>
			"""
			analysis_counter = len(record["analysis"])
			for analysis in record["analysis"]:
				analysis_counter -= 1
				if analysis_counter == 0:
					result += "<tr class='analysis_last_row'>"
				else:
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
					<table class='table table-bordered table-hover table-fixed table-compact mux_table'>
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
						<tbody class='mux_tbody'>
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
			result += "<div class='hidden'>FINAL_NONE</div>"
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
	Main Function
	export FLASK_APP=bcl2fastq_records.py
	flask run --host=0.0.0.0
	"""
	args = instantiate_args()
	mongo = instantiate_mongo(args.testing)
	query = instantiate_query(args)

	if args.flask:
#        os.environ["FLASK_APP"] = os.path.basename(__file__)
#        os.system("flask run --host=0.0.0.0")
		app.run(host="0.0.0.0", port="5000")
	else:
		if args.arrange:
			mongo_found = mongo.find(query).sort(list((j[0], 1) if j[1] == "asc" else (j[0], -1) \
				for j in list(zip([i for i in args.arrange if args.arrange.index(i) % 2 == 0], \
					[i for i in args.arrange if args.arrange.index(i) % 2 == 1]))))
		else:
			mongo_found = mongo.find(query)

		for record in mongo_found:
			result = record
			if len(str(record["timestamp"])) == 13:
				result["timestamp"] = str(datetime.fromtimestamp(
					record["timestamp"] / 1000).isoformat()).replace(":", "-")
			else:
				result["timestamp"] = str(record["timestamp"])
			PrettyPrinter(indent=2).pprint(result)

if __name__ == "__main__":
#    app.run(debug=True, host="0.0.0.0", port="5000")
	main()
