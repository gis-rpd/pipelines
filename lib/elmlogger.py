"""ELM Logging functions
"""

import os
import socket
from datetime import datetime
import subprocess
import json
from collections import OrderedDict
from collections import namedtuple

from pipelines import generate_timestamp


ElmUnit = namedtuple('ElmUnit', [
    'run_id', # without flowcell id
    'library_id',# MUX for bcl2fastq, otherwise (component-)lib
    'lane_id',
    'outdir',
    'library_file_size'])


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
        """disk usage via du. return -1 if not existant"""
        if not os.path.exists(path):
            return -1
        else:
            return int(subprocess.check_output(['du', '-s', path]).split()[0])


    def __init__(self,
                 script_name,# used as logging prefix. can be dummy
                 pipeline_name,
                 pipeline_version,
                 submitter,
                 site,
                 instance_id,
                 log_path,# main logging file
                 elm_units):
        """FIXME:add-doc"""

        assert isinstance(elm_units, list)

        elmlogdir = os.getenv('RPD_ELMLOGDIR')
        assert elmlogdir, ("RPD_ELMLOGDIR undefined")

        pipelogdir = os.path.join(elmlogdir, pipeline_name)
        assert os.path.exists(pipelogdir), (
            "pipeline log dir {} doesn't exist".format(pipelogdir))

        # timestamp just a way to make it unique
        logfile = os.path.join(pipelogdir, generate_timestamp() + ".log")
        assert not os.path.exists(logfile)
        self.logfile = logfile

        # only used as logging prefix (not even parsed by ELM)
        self.script_name = script_name

        # json-like values
        self.fields = OrderedDict()
        # caller provided
        self.fields['pipeline_name'] = pipeline_name
        self.fields['pipeline_version'] = pipeline_version
        self.fields['site'] = site
        self.fields['instance_id'] = instance_id
        self.fields['submitter'] = submitter
        self.fields['log_path'] = log_path
        # internally computed
        self.fields['status_id'] = None

        self.elm_units = elm_units


    def write_event(self):
        """write logging events to file per unit (yes, that's not intuitive)
        """

        with open(self.logfile, 'a') as fh:
            timestr = datetime.now().strftime('%c')
            for eu in self.elm_units:
                # convert None to 'NA' and all to str, except outdir which was only needed for library_file_size
                dump = eu._asdict()
                del dump['outdir']
                for (k, v) in self.fields.items():
                    assert k not in dump
                    dump[k] = str(v) if v else "NA"
                jsonstr = json.dumps(dump)
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
        # update library_file_size per elm unit based on outdir
        self.elm_units = [eu._replace(library_file_size=self.disk_usage(eu.outdir))
                          for eu in self.elm_units]
        self.write_event()
