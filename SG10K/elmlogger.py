"""ELM Logging functions
"""

import os
import socket
from datetime import datetime
import subprocess
import json
from collections import OrderedDict


class ElmLogging(object):
    """
    NOTE:
    - all log lines need all fields
    - one line per runid and lane
    """


    @staticmethod
    def get_hostname():
        return socket.gethostname()


    @staticmethod
    def disk_usage(path):
        """disk usage via du"""
        return int(subprocess.check_output(['du', '-s', path]).split()[0])


    @staticmethod
    def timestamp():
        """returns iso timestamp down to ms"""
        return datetime.now().isoformat()


    def __init__(self,
                 script_name,# used as logging prefix. can be dummy
                 result_outdir,# where results are stored
                 library_id,
                 run_id,
                 lane_id,
                 pipeline_name,
                 pipeline_version,
                 site,
                 instance_id,
                 submitter,
                 log_path):# main logging file
        """FIXME:add-doc"""

        elmlogdir = os.getenv('RPD_ELMLOGDIR')
        assert elmlogdir, ("RPD_ELMLOGDIR undefined")

        pipelogdir = os.path.join(elmlogdir, pipeline_name)
        assert os.path.exists(pipelogdir), (
            "pipeline log dir {} doesn't exist".format(pipelogdir))

        # timestamp just a way to make it unique
        logfile = os.path.join(pipelogdir, self.timestamp() + ".log")
        assert not os.path.exists(logfile)
        # claim name immediately
        open(logfile, 'w').close()
        self.logfile = logfile

        # only used as logging prefix (not even parsed by ELM)
        self.script_name = script_name
        # required for computing library_file_size
        self.result_outdir = result_outdir

        # json-like values
        self.fields = OrderedDict()
        # caller provided
        self.fields['library_id'] = library_id
        self.fields['run_id'] = run_id
        self.fields['lane_id'] = lane_id
        self.fields['pipeline_name'] = pipeline_name
        self.fields['pipeline_version'] = pipeline_version
        self.fields['site'] = site
        self.fields['instance_id'] = instance_id
        self.fields['submitter'] = submitter
        self.fields['log_path'] = log_path
        # internally computed
        self.fields['library_file_size'] = None
        self.fields['status_id'] = None


    def write_event(self):
        """write one logging event to file
        """
        with open(self.logfile, 'a') as fh:
            timestr = datetime.now().strftime('%c')
            # convert None to 'NA' and all to str
            jsonstr = json.dumps({k: str(v) if v else "NA"
                                  for (k, v) in self.fields.items()})
            fh.write('[{}] [{}] [{}] [EVENTLOG] "{}"\n'.format(
                timestr, self.get_hostname(), self.script_name, jsonstr))


    def start(self):
        """Start ELM logging using config values
        """
        # startup
        self.fields['status_id'] = 5
        self.write_event()


    def stop(self, success):
        """Finalize ELM logging
        """
        if success:
            # done
            self.fields['status_id'] = 6
        else:
            # troubleshooting
            self.fields['status_id'] = 7
        self.fields['library_file_size'] = self.disk_usage(
            self.result_outdir)
        self.write_event()
